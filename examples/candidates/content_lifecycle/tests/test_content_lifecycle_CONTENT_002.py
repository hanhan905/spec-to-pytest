"""Adapted historical TRAE test (maintainer review pending) for the minimum title length boundary.

scenario_id: content_lifecycle
case_id: CONTENT_002
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
@allure.story("Title minimum length boundary")
@allure.title("CONTENT_002 标题最小长度 1 个字符可以发布并被搜索到")
@pytest.mark.case_id("CONTENT_002")
@pytest.mark.generated
@pytest.mark.ai_demo
def test_title_minimum_length(authenticated_page: Page, settings: Settings) -> None:
    post = post_data("TITLE_MIN_001")
    publish_page = PublishPage(authenticated_page, settings.base_url)
    with allure.step("Publish content with a single-character title"):
        publish_page.open().fill(post).publish().expect_success()

    feed_page = FeedPage(authenticated_page, settings.base_url)
    with allure.step("Search the published content by title"):
        feed_page.open().search_for(post.title)
        feed_page.expect_post(post.title, post.content)

    assert feed_page.post(post.title).is_visible()
