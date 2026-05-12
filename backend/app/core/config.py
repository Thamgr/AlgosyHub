from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/algosyhub"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_TTL_DAYS: int = 7

    CF_SERVICE_ACCOUNT: str = ""
    CF_SERVICE_PASSWORD: str = ""

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"


settings = Settings()
