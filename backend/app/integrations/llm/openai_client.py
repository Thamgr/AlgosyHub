"""OpenAI-based ``LLMClient`` implementation.

Only constructs the underlying ``AsyncOpenAI`` lazily so the rest of the app
runs even without an API key — falling back to ``StubLLMClient`` when
``OPENAI_API_KEY`` is empty.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.integrations.llm.base import LLMClient

logger = logging.getLogger(__name__)


class OpenAIClient(LLMClient):
    def __init__(self, api_key: str, model: str) -> None:
        self._model = model
        # Imported here so the dependency is only required when actually used.
        from openai import AsyncOpenAI  # type: ignore[import-not-found]

        self._client = AsyncOpenAI(api_key=api_key)

    async def chat(self, messages: list[dict[str, Any]]) -> str:
        # JSON mode lets us reliably parse the hint structure. If the caller
        # didn't ask for JSON in their prompt, OpenAI will still return JSON
        # (a single key like {"text": "..."}), but the heuristic parser
        # downstream handles non-strict shapes gracefully.
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.4,
            response_format={"type": "json_object"},
        )
        return resp.choices[0].message.content or ""


class StubLLMClient(LLMClient):
    """Offline fallback used when no API key is configured.

    Returns deterministic placeholder text so the UI works end-to-end in
    local development without burning real LLM credits.
    """

    async def chat(self, messages: list[dict[str, Any]]) -> str:
        user_msg = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"),
            "",
        )
        return (
            "[LLM не настроен — пример подсказки]\n\n"
            "Заглушка вернула ответ потому, что переменная OPENAI_API_KEY пустая. "
            "Чтобы получать настоящие подсказки от модели, заполните ключ в .env.\n\n"
            f"Запрос пользователя: {user_msg[:200]}"
        )


def make_default_client() -> LLMClient:
    if settings.OPENAI_API_KEY:
        try:
            return OpenAIClient(settings.OPENAI_API_KEY, settings.OPENAI_MODEL)
        except Exception:
            logger.exception("Failed to initialise OpenAI client, falling back to stub")
    return StubLLMClient()
