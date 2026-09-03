"""Adapted historical TRAE test (maintainer review pending) for the blank title rejection.

scenario_id: content_lifecycle
case_id: CONTENT_004
original_run_id: 20260821T163455Z-content_lifecycle-8aafd9
"""

from __future__ import annotations

import allure
import pytest
from playwright.sync_api import Page, expect

from framework.config.settings import Settings
from framework.data.content import post_data
from framework.pages.publish_page import PublishPage


@allure.epic("AI-generated testing demo")
@allure.feature("Local content community")
@allure.story("Blank title rejection")
@allure.title("CONTENT_004 空白标题被拒绝且不创建内容")
@pytest.mark.case_id("CONTENT_004")
@pytest.mark.generated
@pytest.mark.ai_demo
def test_blank_title_rejected(authenticated_page: Page, settings: Settings) -> None:
    post = post_data("TITLE_BLANK")
    publish_page = PublishPage(authenticated_page, settings.base_url)
    with allure.step("Submit a whitespace-only title"):
        publish_page.open().fill(post).publish()

    with allure.step("Verify the publish error shows and success stays hidden"):
        expect(publish_page.error).to_be_visible()
        expect(publish_page.error).to_have_text("Title must not be blank")
        expect(publish_page.success).to_be_hidden()

    with allure.step("Verify no content was created"):
        listing = authenticated_page.request.get(f"{settings.api_url}/api/posts").json()
        assert listing["total"] == 0
