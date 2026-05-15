"""Universal OpenAI-compatible ``LLMClient`` implementation.

Один и тот же класс используется и для OpenAI, и для Yandex Cloud
Foundation Models, и для любого другого OpenAI-совместимого провайдера.
Различия задаются через переменные окружения:

* ``OPENAI_API_KEY`` — токен;
* ``OPENAI_BASE_URL`` — базовый URL (пусто = OpenAI по умолчанию);
* ``OPENAI_MODEL`` — имя модели (например ``gpt-4o-mini`` или
  ``deepseek-v32/latest``);
* ``OPENAI_PROJECT`` — необязательный заголовок ``OpenAI-Project``;
  для Яндекса сюда кладут folder_id, и тогда финальный идентификатор
  модели автоматически собирается в URI ``gpt://<project>/<model>``.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.integrations.llm.base import LLMClient

logger = logging.getLogger(__name__)


def _resolve_model_id(model: str, project: str) -> str:
    """Build the actual model identifier sent to the provider.

    Если пользователь уже передал полный URI (``gpt://...``) — оставляем
    как есть. Иначе при наличии ``project`` оборачиваем имя модели в
    URI Яндекса ``gpt://<project>/<model>``. Без project — просто имя.
    """
    if "://" in model:
        return model
    if project:
        return f"gpt://{project}/{model}"
    return model


class OpenAIClient(LLMClient):
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "",
        project: str = "",
        timeout: float = 90.0,
    ) -> None:
        self._model = _resolve_model_id(model, project)
        # Импорт здесь, чтобы зависимость требовалась только при реальном
        # использовании клиента.
        from openai import AsyncOpenAI  # type: ignore[import-not-found]

        kwargs: dict[str, Any] = {"api_key": api_key, "timeout": timeout}
        if base_url:
            kwargs["base_url"] = base_url
        if project:
            kwargs["project"] = project
        self._client = AsyncOpenAI(**kwargs)

    async def chat(self, messages: list[dict[str, Any]]) -> str:
        # Не используем response_format=json_object: его поддерживает не
        # каждый совместимый провайдер. Структуру JSON просим в
        # системном промпте, а парсер на стороне сервиса умеет
        # деградировать на нестрогий ответ.
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.1,
            reasoning_effort="none"
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
            return OpenAIClient(
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_MODEL,
                base_url=settings.OPENAI_BASE_URL,
                project=settings.OPENAI_PROJECT,
                timeout=settings.OPENAI_TIMEOUT,
            )
        except Exception:
            logger.exception("Failed to initialise OpenAI client, falling back to stub")
    return StubLLMClient()
