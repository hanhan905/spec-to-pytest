"""Historical TRAE candidate: search matching and tag de-duplication.

scenario_id: content_lifecycle
case_id: CONTENT_013
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
@allure.story("Search matching and tag de-duplication")
@allure.title("CONTENT_013 搜索匹配正文和标签且不区分大小写并验证标签去重")
@pytest.mark.case_id("CONTENT_013")
@pytest.mark.generated
@pytest.mark.ai_demo
def test_search_matching_and_tag_dedup(authenticated_page: Page, settings: Settings) -> None:
    post = post_data("TAGS_DEDUP")
    with allure.step("Publish content with duplicate and padded tags"):
        PublishPage(authenticated_page, settings.base_url).open().fill(
            post
        ).publish().expect_success()

    feed_page = FeedPage(authenticated_page, settings.base_url)
    with allure.step("Verify tags are de-duplicated in first-occurrence order"):
        feed_page.open().search_for(post.title)
        card = feed_page.post(post.title)
        expect(card).to_be_visible()
        assert card.locator(".tag").all_text_contents() == ["AI测试", "Playwright"]

    with allure.step("Search by a body substring and verify a match"):
        feed_page.search_for("搜索和标签去重")
        expect(feed_page.post(post.title)).to_be_visible()

    with allure.step("Search by tag and verify a match"):
        feed_page.search_for("Playwright")
        expect(feed_page.post(post.title)).to_be_visible()

    with allure.step("Search with different casing and verify a match"):
        feed_page.search_for("playwright")
        expect(feed_page.post(post.title)).to_be_visible()
