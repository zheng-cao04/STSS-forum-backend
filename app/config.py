from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "STSS Forum Backend"
    env: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./data/forum.db"
    upload_dir: str = "uploads"
    public_upload_prefix: str = "/uploads"
    frontend_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    skip_external_checks: bool = True
    info_service_url: str = "http://localhost:8002"
    course_selection_service_url: str = "http://localhost:8003"
    score_service_url: str = "http://localhost:8004"
    internal_token: str = "dev-internal-token"

    @field_validator("frontend_origins", mode="before")
    @classmethod
    def split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
