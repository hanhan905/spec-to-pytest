"""Adapted historical TRAE test (maintainer review pending) for persistence across navigation.

scenario_id: content_lifecycle
case_id: CONTENT_011
original_run_id: 20260821T163455Z-content_lifecycle-8aafd9
"""

from __future__ import annotations

import allure
import pytest
from playwright.sync_api import Page, expect

from framework.config.settings import Settings
from framework.data.content import post_data
from framework.pages.dashboard_page import DashboardPage
from framework.pages.feed_page import FeedPage
from framework.pages.publish_page import PublishPage


@allure.epic("AI-generated testing demo")
@allure.feature("Local content community")
@allure.story("Persistence across navigation")
@allure.title("CONTENT_011 发布点赞评论后离开页面再返回状态保留")
@pytest.mark.case_id("CONTENT_011")
@pytest.mark.generated
@pytest.mark.ai_demo
def test_state_persists_across_navigation(authenticated_page: Page, settings: Settings) -> None:
    post = post_data("PERSIST_BASE")
    with allure.step("Publish, like and comment on the content"):
        PublishPage(authenticated_page, settings.base_url).open().fill(
            post
        ).publish().expect_success()
        feed_page = FeedPage(authenticated_page, settings.base_url)
        feed_page.open().search_for(post.title)
        feed_page.like(post.title)
        feed_page.comment(post.title, post.comment)

    with allure.step("Navigate away to the dashboard"):
        dashboard = DashboardPage(authenticated_page, settings.base_url)
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        dashboard.wait_until_loaded()

    with allure.step("Return to the feed and verify persisted state"):
        feed_page.open().search_for(post.title)
        like_button = authenticated_page.get_by_role("button", name=f"点赞：{post.title}")
        expect(like_button).to_have_attribute("aria-pressed", "true")
        expect(like_button).to_have_text("点赞 1")
        expect(feed_page.post(post.title).get_by_text("评论 1", exact=True)).to_be_visible()
