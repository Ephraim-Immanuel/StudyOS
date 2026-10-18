"""Application settings, read from environment variables / the .env file."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://studyos:studyos@localhost:5432/studyos"
    cors_origins: str = "http://localhost:5173"
    cookie_name: str = "studyos_session"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    session_expire_days: int = 7
    default_timezone: str = "Asia/Kolkata"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
