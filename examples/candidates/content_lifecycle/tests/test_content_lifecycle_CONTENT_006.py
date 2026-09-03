"""Adapted historical TRAE test (maintainer review pending) for the minimum content length boundary.

scenario_id: content_lifecycle
case_id: CONTENT_006
original_run_id: 20260821T163455Z-content_lifecycle-8aafd9
"""

from __future__ import annotations

import allure
import pytest
from playwright.sync_api import Page, expect

from framework.config.settings import Settings
from framework.data.content import post_data
from framework.pages.feed_page import FeedPage
from framework.pages.publish_page import PublishPage


@allure.epic("AI-generated testing demo")
@allure.feature("Local content community")
@allure.story("Content minimum length boundary")
@allure.title("CONTENT_006 正文最小长度 1 个字符可以发布")
@pytest.mark.case_id("CONTENT_006")
@pytest.mark.generated
@pytest.mark.ai_demo
def test_content_minimum_length(authenticated_page: Page, settings: Settings) -> None:
    post = post_data("CONTENT_MIN_001")
    publish_page = PublishPage(authenticated_page, settings.base_url)
    with allure.step("Publish content with a single-character body"):
        publish_page.open().fill(post).publish().expect_success()

    feed_page = FeedPage(authenticated_page, settings.base_url)
    with allure.step("Search and verify the single-character body is shown"):
        feed_page.open().search_for(post.title)
        card = feed_page.post(post.title)
        expect(card).to_be_visible()
        expect(card.locator(".post-content")).to_have_text(post.content)
