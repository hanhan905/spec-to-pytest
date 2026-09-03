"""Adapted historical TRAE test (maintainer review pending) for like toggle state and persistence.

scenario_id: content_lifecycle
case_id: CONTENT_010
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
@allure.story("Like toggle state and persistence")
@allure.title("CONTENT_010 重复点赞切换状态且刷新后计数保持一致")
@pytest.mark.case_id("CONTENT_010")
@pytest.mark.generated
@pytest.mark.ai_demo
def test_like_toggle_and_reload(authenticated_page: Page, settings: Settings) -> None:
    post = post_data("LIKE_BASE")
    PublishPage(authenticated_page, settings.base_url).open().fill(post).publish().expect_success()

    feed_page = FeedPage(authenticated_page, settings.base_url)
    feed_page.open().search_for(post.title)
    like_button = authenticated_page.get_by_role("button", name=f"点赞：{post.title}")

    with allure.step("Like the content and verify pressed state with count 1"):
        feed_page.like(post.title)

    with allure.step("Unlike the content and verify released state with count 0"):
        like_button.click()
        expect(like_button).to_have_attribute("aria-pressed", "false")
        expect(like_button).to_have_text("点赞 0")

    with allure.step("Reload and verify the released state persists"):
        feed_page.page.reload()
        expect(like_button).to_have_attribute("aria-pressed", "false")
        expect(like_button).to_have_text("点赞 0")
