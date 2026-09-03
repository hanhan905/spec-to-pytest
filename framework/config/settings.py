"""Typed configuration with deterministic override precedence."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from framework.runtime.service import parse_local_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AUTO_",
        extra="ignore",
        case_sensitive=False,
    )

    environment: str = "local"
    base_url: str = "http://127.0.0.1:8000"
    api_url: str = "http://127.0.0.1:8000"
    control_token: SecretStr = SecretStr("")
    instance_id: str = ""
    default_timeout_ms: int = Field(default=5_000, ge=100)
    navigation_timeout_ms: int = Field(default=10_000, ge=100)
    artifacts_dir: Path = Path("reports/artifacts")

    @field_validator("base_url", "api_url")
    @classmethod
    def require_local_origin(cls, value: str) -> str:
        return parse_local_url(value)[0]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return one immutable-by-convention settings object per test process."""
    return Settings()


def settings_with_overrides(**overrides: object) -> Settings:
    """Build settings for CLI/test overrides without mutating process environment."""
    base = get_settings().model_dump()
    base.update({key: value for key, value in overrides.items() if value is not None})
    return Settings.model_validate(base)
