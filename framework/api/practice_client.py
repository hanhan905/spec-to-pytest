"""Typed HTTPX client for fast API setup and API-level assertions."""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import SecretStr

from framework.data.models import Credentials


class PracticeApiClient:
    def __init__(
        self, base_url: str, timeout_seconds: float = 5.0, control_token: SecretStr | None = None
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout_seconds,
            trust_env=False,
            headers={"Origin": base_url.rstrip("/")},
        )
        self._control_token = control_token or SecretStr("")

    def __enter__(self) -> PracticeApiClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def health(self) -> httpx.Response:
        return self._client.get("/health")

    def login(self, credentials: Credentials) -> httpx.Response:
        return self._client.post(
            "/api/login",
            json={"username": credentials.username, "password": credentials.password},
        )

    def profile(self) -> httpx.Response:
        return self._client.get("/api/profile")

    def items(self, **params: Any) -> httpx.Response:
        return self._client.get("/api/items", params=params)

    def posts(self, **params: Any) -> httpx.Response:
        return self._client.get("/api/posts", params=params)

    def create_post(self, data: dict[str, str], files: Any = None) -> httpx.Response:
        return self._client.post("/api/posts", data=data, files=files)

    def toggle_like(self, post_id: int) -> httpx.Response:
        return self._client.post(f"/api/posts/{post_id}/like")

    def add_comment(self, post_id: int, text: str) -> httpx.Response:
        return self._client.post(f"/api/posts/{post_id}/comments", json={"text": text})

    def reset(self) -> httpx.Response:
        return self._client.post(
            "/api/reset", headers={"X-Practice-Control": self._control_token.get_secret_value()}
        )
