from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    github_client_id: str
    github_client_secret: str
    github_redirect_uri: str = "http://127.0.0.1:8000/auth/github/callback"
    frontend_url: str = "http://localhost:5173"
    session_secret: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()