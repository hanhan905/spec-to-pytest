"""Adapted historical TRAE test (maintainer review pending) for the maximum title length boundary.

scenario_id: content_lifecycle
case_id: CONTENT_003
original_run_id: 20260821T163455Z-content_lifecycle-8aafd9
"""

from __future__ import annotations

import allure
import pytest
from playwright.sync_api import Page

from framework.config.settings import Settings
from framework.data.content import post_data
from framework.pages.feed_page import FeedPage
from framework.pages.publish_page import PublishPage


@allure.epic("AI-generated testing demo")
@allure.feature("Local content community")
@allure.story("Title maximum length boundary")
@allure.title("CONTENT_003 标题最大长度 50 个字符可以发布且完整保存")
@pytest.mark.case_id("CONTENT_003")
@pytest.mark.generated
@pytest.mark.ai_demo
def test_title_maximum_length(authenticated_page: Page, settings: Settings) -> None:
    post = post_data("TITLE_MAX_050")
    publish_page = PublishPage(authenticated_page, settings.base_url)
    with allure.step("Publish content with a 50-character title"):
        publish_page.open().fill(post).publish().expect_success()

    feed_page = FeedPage(authenticated_page, settings.base_url)
    with allure.step("Search and verify the full 50-character title is preserved"):
        feed_page.open().search_for(post.title)
        card = feed_page.post(post.title)
        heading = card.get_by_role("heading", name=post.title)
        assert len(heading.inner_text()) == 50
