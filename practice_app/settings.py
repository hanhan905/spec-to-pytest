"""Explicit instance configuration; no files are created at import time."""

from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PRACTICE_", extra="ignore")

    data_dir: Path = Path(".local/app")
    origin: str = "http://127.0.0.1:8000"
    instance_id: str = Field(default_factory=lambda: uuid4().hex)
    bug_mode: Literal["healthy", "comment_counter"] = "healthy"
    testing: bool = False
    control_token: SecretStr = SecretStr("")
    session_seconds: int = Field(default=3600, ge=1, le=86400)

    @field_validator("origin")
    @classmethod
    def local_origin(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "localhost", "testserver"}
            or parsed.username
            or parsed.password
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("origin must be an exact local HTTP origin")
        return value.rstrip("/")

    @model_validator(mode="after")
    def require_test_control(self) -> "AppSettings":
        if self.testing and not self.control_token.get_secret_value():
            raise ValueError("testing mode requires a control token")
        return self
