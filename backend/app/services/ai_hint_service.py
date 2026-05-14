"""Three-level AI hints for problems.

The user clicks through three escalating hints on the problem page:

* hint1 — a gentle nudge (idea direction, no spoilers)
* hint2 — the core algorithmic idea / data structures, no code
* hint3 — full solution sketch with complexity (the "give up" button)

Hints are problem-specific, not user-specific, so we cache one row per
problem in ``problem_hints``. The model is called only on the first request
for a problem, then served from the cache.
"""

from __future__ import annotations

import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.integrations.llm.base import LLMClient
from app.integrations.llm.openai_client import make_default_client
from app.models.problem import Problem
from app.models.problem_hint import ProblemHint

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Ты опытный тренер по спортивному программированию. Тебе дают задачу с "
    "Codeforces и просят придумать три уровня подсказок:\n"
    "1) Лёгкая подсказка: только направление мысли, без раскрытия идеи.\n"
    "2) Средняя подсказка: ключевая алгоритмическая идея и структуры данных, "
    "   но без готового кода.\n"
    "3) Полное решение: подробный алгоритм со сложностью и (если уместно) "
    "   псевдокодом. Это уровень «сдаюсь».\n"
    "Каждая подсказка — отдельный шаг, не повторяй предыдущие. "
    "Отвечай только валидным JSON вида {\"hint1\": \"...\", \"hint2\": \"...\", \"hint3\": \"...\"}. "
    "Подсказки на русском языке."
)


def _build_user_prompt(problem: Problem) -> str:
    return (
        f"Задача: {problem.title}\n"
        f"Источник: {problem.external_source.value} {problem.external_id}\n"
        f"Сложность: {problem.difficulty or 'не указана'}\n"
        f"Теги: {', '.join(problem.tags) if problem.tags else '—'}\n"
        f"Условие: см. {problem.external_url}\n\n"
        "Сгенерируй три подсказки в JSON-формате, как описано в системном сообщении."
    )


# Singleton so we don't reconstruct the LLM client on every request.
_llm: LLMClient | None = None


def _get_llm() -> LLMClient:
    global _llm
    if _llm is None:
        _llm = make_default_client()
    return _llm


def _parse_hints(raw: str) -> tuple[str, str, str]:
    """Pull three hints out of an LLM response.

    Falls back gracefully if the model returned non-JSON text — we treat the
    whole reply as ``hint3`` and use generic placeholders for the earlier
    levels. This way the UI never breaks on a malformed response.
    """
    text = raw.strip()
    if text.startswith("```"):
        # Strip ```json ... ``` fences.
        text = text.split("\n", 1)[-1] if "\n" in text else text
        if text.endswith("```"):
            text = text[: -3]
    try:
        data = json.loads(text)
        h1 = str(data.get("hint1") or "").strip()
        h2 = str(data.get("hint2") or "").strip()
        h3 = str(data.get("hint3") or "").strip()
        if h1 and h2 and h3:
            return h1, h2, h3
    except json.JSONDecodeError:
        logger.warning("LLM hints response is not valid JSON")

    return (
        "Подсказка не сгенерирована — модель вернула неструктурированный ответ. "
        "Попробуйте перегенерировать.",
        "Подсказка не сгенерирована — модель вернула неструктурированный ответ.",
        raw.strip(),
    )


async def get_or_generate(
    session: AsyncSession, problem_id: int
) -> ProblemHint:
    cached = await session.get(ProblemHint, problem_id)
    if cached is not None:
        return cached

    problem = await session.get(Problem, problem_id)
    if problem is None:
        raise AppError("Problem not found", 404)

    raw = await _get_llm().chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(problem)},
        ]
    )
    hint1, hint2, hint3 = _parse_hints(raw)

    hint = ProblemHint(
        problem_id=problem_id, hint1=hint1, hint2=hint2, hint3=hint3
    )
    session.add(hint)
    await session.flush()
    await session.refresh(hint)
    return hint


async def regenerate(session: AsyncSession, problem_id: int) -> ProblemHint:
    existing = await session.get(ProblemHint, problem_id)
    if existing is not None:
        await session.delete(existing)
        await session.flush()
    return await get_or_generate(session, problem_id)


async def get_cached(session: AsyncSession, problem_id: int) -> ProblemHint | None:
    return await session.get(ProblemHint, problem_id)


async def find_for_problems(
    session: AsyncSession, problem_ids: list[int]
) -> dict[int, ProblemHint]:
    if not problem_ids:
        return {}
    result = await session.execute(
        select(ProblemHint).where(ProblemHint.problem_id.in_(problem_ids))
    )
    return {h.problem_id: h for h in result.scalars().all()}
