"""Adapted historical TRAE test (maintainer review pending) for the content lifecycle main flow.

scenario_id: content_lifecycle
case_id: CONTENT_001
original_run_id: 20260821T163455Z-content_lifecycle-8aafd9
"""

from __future__ import annotations

import allure
import pytest
from playwright.sync_api import Page, expect

from framework.config.settings import Settings
from framework.data.content import post_data
from framework.workflows.content_workflow import ContentLifecycleWorkflow


@allure.epic("AI-generated testing demo")
@allure.feature("Local content community")
@allure.story("Publish, search, like, comment and persist")
@allure.title("CONTENT_001 发布内容后可搜索、点赞和评论并刷新验证持久化")
@pytest.mark.case_id("CONTENT_001")
@pytest.mark.generated
@pytest.mark.ai_demo
def test_content_lifecycle_main_flow(authenticated_page: Page, settings: Settings) -> None:
    post = post_data("BASE_001")
    with allure.step("Publish, search, like and comment via the lifecycle workflow"):
        feed = ContentLifecycleWorkflow(authenticated_page, settings.base_url)
        feed.publish_search_like_and_comment(post)

    with allure.step("Reload the feed and verify persisted state"):
        feed.feed_page.page.reload()
        card = feed.feed_page.post(post.title)
        expect(card).to_be_visible()
        like_button = authenticated_page.get_by_role("button", name=f"点赞：{post.title}")
        expect(like_button).to_have_attribute("aria-pressed", "true")
        expect(like_button).to_have_text("点赞 1")
        expect(card.get_by_text("评论 1", exact=True)).to_be_visible()
