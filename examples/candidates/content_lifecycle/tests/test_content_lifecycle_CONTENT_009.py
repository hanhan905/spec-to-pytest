"""Adapted historical TRAE test (maintainer review pending) for unauthenticated access redirection.

scenario_id: content_lifecycle
case_id: CONTENT_009
original_run_id: 20260821T163455Z-content_lifecycle-8aafd9
"""

from __future__ import annotations

import re

import allure
import pytest
from playwright.sync_api import Page, expect

from framework.config.settings import Settings


@allure.epic("AI-generated testing demo")
@allure.feature("Local content community")
@allure.story("Unauthenticated access redirection")
@allure.title("CONTENT_009 未登录用户访问发布页和内容广场跳转到登录页")
@pytest.mark.case_id("CONTENT_009")
@pytest.mark.generated
@pytest.mark.ai_demo
def test_unauthenticated_access_redirects_to_login(
    configured_page: Page, settings: Settings
) -> None:
    login_url = re.compile(r"/login$")

    with allure.step("Visit /publish without a session"):
        configured_page.goto(f"{settings.base_url}/publish")
        expect(configured_page).to_have_url(login_url)
        expect(configured_page.get_by_role("heading", name="发布内容")).to_have_count(0)

    with allure.step("Visit /feed without a session"):
        configured_page.goto(f"{settings.base_url}/feed")
        expect(configured_page).to_have_url(login_url)
        expect(configured_page.get_by_role("heading", name="内容广场")).to_have_count(0)
