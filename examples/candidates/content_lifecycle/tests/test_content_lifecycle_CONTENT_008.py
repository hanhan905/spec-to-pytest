"""Adapted historical TRAE test (maintainer review pending) for search empty states.

scenario_id: content_lifecycle
case_id: CONTENT_008
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
@allure.story("Search empty states")
@allure.title("CONTENT_008 搜索无匹配与空广场显示正确的空状态")
@pytest.mark.case_id("CONTENT_008")
@pytest.mark.generated
@pytest.mark.ai_demo
def test_search_empty_states(authenticated_page: Page, settings: Settings) -> None:
    feed_page = FeedPage(authenticated_page, settings.base_url)
    with allure.step("Open the feed and verify the empty-feed guidance"):
        feed_page.open()
        expect(authenticated_page.get_by_text("暂无内容，发布第一条内容吧")).to_be_visible()
        expect(authenticated_page.get_by_role("article")).to_have_count(0)

    post = post_data("BASE_001")
    with allure.step("Publish one content item"):
        PublishPage(authenticated_page, settings.base_url).open().fill(
            post
        ).publish().expect_success()

    with allure.step("Search a unique non-matching keyword"):
        feed_page.open().search_for("ZZZ不存在的关键词XYZ")

    with allure.step("Verify the no-match empty state and no content cards"):
        expect(authenticated_page.get_by_text("没有找到匹配内容")).to_be_visible()
        expect(authenticated_page.get_by_role("article")).to_have_count(0)
