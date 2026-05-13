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

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Comma-separated list of allowed CORS origins.
    # Use "*" to allow any origin (sets allow_origin_regex=".*" under the hood).
    CORS_ORIGINS: str = "*"


settings = Settings()
