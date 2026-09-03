"""Failure hooks that attach evidence while the Playwright page is still alive."""

from __future__ import annotations

import json
import logging
import shutil
from collections.abc import Generator
from pathlib import Path
from typing import cast

import allure
import pytest
from _pytest.reports import TestReport
from playwright.sync_api import Page
from pluggy import Result

from framework.artifacts.network_recorder import NetworkRecorder
from framework.config.settings import get_settings


def pytest_sessionstart(session: pytest.Session) -> None:
    results_dir_value = getattr(session.config.option, "allure_report_dir", None)
    if not results_dir_value:
        return
    results_dir = Path(results_dir_value)
    results_dir.mkdir(parents=True, exist_ok=True)
    settings = get_settings()
    environment = "\n".join(
        [
            f"Environment={settings.environment}",
            f"BaseURL={settings.base_url}",
            "Framework=Python + Pytest + Playwright",
        ]
    )
    (results_dir / "environment.properties").write_text(environment, encoding="utf-8")
    categories = Path("config/allure/categories.json")
    if categories.exists():
        shutil.copyfile(categories, results_dir / "categories.json")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, Result[TestReport], None]:
    outcome = yield
    report = outcome.get_result()
    if not report.failed:
        return

    function_item = cast(pytest.Function, item)
    page = function_item.funcargs.get("configured_page") or function_item.funcargs.get("page")
    if isinstance(page, Page) and not page.is_closed():
        try:
            allure.attach(
                page.screenshot(full_page=True),
                name="failure-screenshot",
                attachment_type=allure.attachment_type.PNG,
            )
            allure.attach(
                page.content(), name="page-source", attachment_type=allure.attachment_type.HTML
            )
        except Exception as error:
            logging.getLogger(__name__).warning(
                "Evidence capture unavailable: %s", type(error).__name__
            )

    recorder = function_item.funcargs.get("network_recorder")
    if isinstance(recorder, NetworkRecorder):
        try:
            allure.attach(
                json.dumps(recorder.serializable(), ensure_ascii=False, indent=2),
                name="network-responses",
                attachment_type=allure.attachment_type.JSON,
            )
        except Exception as error:
            logging.getLogger(__name__).warning(
                "Network evidence unavailable: %s", type(error).__name__
            )
