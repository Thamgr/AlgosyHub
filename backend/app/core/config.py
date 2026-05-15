from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/algosyhub"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_TTL_DAYS: int = 7

    # CF API key/secret для приватных API (опционально). Для опроса публичных
    # посылок через user.status не требуются.
    CF_API_KEY: str = ""
    CF_API_SECRET: str = ""

    # Универсальный OpenAI-совместимый клиент. Подходит и для самого
    # OpenAI, и для Yandex Cloud Foundation Models, и для других
    # совместимых провайдеров — отличаются только base_url, имя модели
    # и (опционально) project (он же folder_id у Яндекса). Если задан
    # OPENAI_PROJECT, его значение используется и как заголовок
    # ``OpenAI-Project``, и как префикс URI модели вида
    # ``gpt://<project>/<model>``.
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str = ""
    OPENAI_PROJECT: str = ""
    # Таймаут одного LLM-запроса, секунд. По умолчанию SDK ждёт 600 с,
    # это слишком долго — снаружи nginx и так упадёт раньше. Явный
    # короткий таймаут даёт понятную ошибку в логах.
    OPENAI_TIMEOUT: float = 90.0
    # Режим reasoning/thinking для моделей, которые его поддерживают
    # (DeepSeek-v3.2 в Yandex Cloud и т.п.). Значения соответствуют
    # ReasoningOptions.mode в API Яндекса: ``DISABLED``,
    # ``ENABLED_HIDDEN``. Пустая строка — не передавать параметр и
    # оставить поведение провайдера по умолчанию. По умолчанию
    # выключаем: подсказки короткие, рассуждать вслух модели не нужно,
    # это экономит токены и сокращает латентность.
    OPENAI_REASONING_MODE: str = "DISABLED"

    # Comma-separated list of allowed CORS origins.
    # Use "*" to allow any origin (sets allow_origin_regex=".*" under the hood).
    CORS_ORIGINS: str = "*"


settings = Settings()
