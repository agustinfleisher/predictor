"""
Configuration for the FastAPI app.
"""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    secret_key: str = Field(default="dev-secret-key-change-me", env="APP_SECRET_KEY")
    access_token_expire_minutes: int = Field(default=60, env="APP_ACCESS_TOKEN_MIN")
    database_path: str = Field(default="app_data.db", env="APP_DATABASE_PATH")

    max_tickers: int = Field(default=5, env="APP_MAX_TICKERS")
    max_days: int = Field(default=365 * 5, env="APP_MAX_DAYS")
    max_upload_rows: int = Field(default=20000, env="APP_MAX_UPLOAD_ROWS")

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def resolve_db_path(settings: Settings) -> str:
    path = settings.database_path
    if os.path.isabs(path):
        return path
    return os.path.join(os.getcwd(), path)
