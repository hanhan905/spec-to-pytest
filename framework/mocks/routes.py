"""Reusable Playwright network interception examples."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from playwright.sync_api import Page, Route


def mock_items(page: Page, items: Sequence[dict[str, Any]]) -> None:
    page.route(
        "**/api/items**",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            json={"items": list(items), "total": len(items), "page": 1, "page_size": 50},
        ),
    )


def mock_items_error(page: Page, status: int = 500) -> None:
    page.route(
        "**/api/items**",
        lambda route: route.fulfill(
            status=status,
            content_type="application/json",
            json={"detail": "Mocked upstream failure"},
        ),
    )


def append_item_to_real_response(page: Page, extra_item: dict[str, Any]) -> None:
    def patch_response(route: Route) -> None:
        response = route.fetch()
        payload = response.json()
        payload["items"].append(extra_item)
        payload["total"] += 1
        route.fulfill(response=response, json=payload)

    page.route("**/api/items**", patch_response)
