"""Composable fixtures layered on top of pytest-playwright's official fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from playwright.sync_api import Browser, BrowserContext, Page

from framework.api.practice_client import PracticeApiClient
from framework.artifacts.network_recorder import NetworkRecorder
from framework.config.settings import Settings
from framework.data.factories import admin_credentials
from framework.workflows.auth_workflow import AuthWorkflow


@pytest.fixture
def browser_context_args(
    browser_context_args: dict[str, object], settings: Settings
) -> dict[str, object]:
    return {
        **browser_context_args,
        "viewport": {"width": 1440, "height": 900},
        "service_workers": "block",
        "base_url": settings.base_url,
    }


@pytest.fixture
def clean_business_state(settings: Settings) -> Iterator[None]:
    with PracticeApiClient(settings.api_url, control_token=settings.control_token) as client:
        assert client.health().json()["instance_id"] == settings.instance_id
        assert client.reset().status_code == 204
    yield


@pytest.fixture
def configured_page(page: Page, settings: Settings, clean_business_state: None) -> Page:
    page.set_default_timeout(settings.default_timeout_ms)
    page.set_default_navigation_timeout(settings.navigation_timeout_ms)
    return page


@pytest.fixture
def network_recorder(configured_page: Page) -> NetworkRecorder:
    return NetworkRecorder(configured_page)


@pytest.fixture
def authenticated_page(configured_page: Page, settings: Settings) -> Page:
    AuthWorkflow(configured_page, settings.base_url).login(admin_credentials())
    return configured_page


@pytest.fixture
def isolated_authenticated_context(
    browser: Browser, settings: Settings
) -> Iterator[BrowserContext]:
    context = browser.new_context(base_url=settings.base_url)
    page = context.new_page()
    AuthWorkflow(page, settings.base_url).login(admin_credentials())
    state = context.storage_state()
    context.close()
    isolated = browser.new_context(base_url=settings.base_url, storage_state=state)
    yield isolated
    isolated.close()
