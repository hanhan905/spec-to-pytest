"""Historical TRAE candidate: comment boundaries and count consistency.

scenario_id: content_lifecycle
case_id: CONTENT_012
original_run_id: 20260821T163455Z-content_lifecycle-8aafd9
"""

from __future__ import annotations

import json

import allure
import pytest
from playwright.sync_api import Page, expect

from framework.config.settings import Settings
from framework.data.content import load_row, post_data
from framework.pages.feed_page import FeedPage
from framework.pages.publish_page import PublishPage


def _submit_comment(page: Page, title: str, text: str, count: int) -> None:
    card = FeedPage(page, "").post(title)
    card.get_by_label(f"评论内容：{title}").fill(text)
    card.get_by_role("button", name="提交评论").click()
    expect(card.locator(".comment-list")).to_contain_text(text)
    expect(card.get_by_text(f"评论 {count}", exact=True)).to_be_visible()


@allure.epic("AI-generated testing demo")
@allure.feature("Local content community")
@allure.story("Comment length boundaries and count")
@allure.title("CONTENT_012 评论长度边界与计数一致")
@pytest.mark.case_id("CONTENT_012")
@pytest.mark.generated
@pytest.mark.ai_demo
def test_comment_boundaries_and_count(authenticated_page: Page, settings: Settings) -> None:
    post = post_data("COMMENT_BASE")
    PublishPage(authenticated_page, settings.base_url).open().fill(post).publish().expect_success()
    feed_page = FeedPage(authenticated_page, settings.base_url)
    feed_page.open().search_for(post.title)

    min_comment = load_row("COMMENT_MIN_001")["comment"]
    max_comment = load_row("COMMENT_MAX_100")["comment"]
    over_comment = load_row("COMMENT_OVER_101")["comment"]
    assert (len(min_comment), len(max_comment), len(over_comment)) == (1, 100, 101)

    with allure.step("Submit a 1-character comment and verify count 1"):
        _submit_comment(authenticated_page, post.title, min_comment, 1)

    with allure.step("Submit a 100-character comment and verify count 2"):
        _submit_comment(authenticated_page, post.title, max_comment, 2)

    with allure.step("Submit a 101-character comment via the API and verify rejection"):
        post_id = authenticated_page.request.get(
            f"{settings.api_url}/api/posts", params={"q": post.title}
        ).json()["posts"][0]["id"]
        response = authenticated_page.request.post(
            f"{settings.api_url}/api/posts/{post_id}/comments",
            data=json.dumps({"text": over_comment}),
            headers={"Content-Type": "application/json"},
        )
        assert response.status == 422

    with allure.step("Verify the comment count stays consistent at 2"):
        listing = authenticated_page.request.get(
            f"{settings.api_url}/api/posts", params={"q": post.title}
        ).json()
        assert listing["posts"][0]["comment_count"] == 2
        expect(feed_page.post(post.title).get_by_text("评论 2", exact=True)).to_be_visible()
