from functools import lru_cache

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_BASE_URL = "https://www.reinfolib.mlit.go.jp/ex-api/external/"


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or .env."""

    api_key: str = Field(alias="MLIT_API_KEY")
    base_url: HttpUrl | str = Field(default=DEFAULT_BASE_URL, alias="MLIT_BASE_URL")
    http_timeout: float = Field(default=15.0, alias="HTTP_TIMEOUT")
    max_concurrency: int = Field(default=4, alias="MAX_CONCURRENCY")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()

