"""Cross-page workflow used by human and AI-generated tests."""

from __future__ import annotations

from playwright.sync_api import Page

from framework.data.models import CommunityPostData
from framework.pages.feed_page import FeedPage
from framework.pages.publish_page import PublishPage


class ContentLifecycleWorkflow:
    def __init__(self, page: Page, base_url: str) -> None:
        self.publish_page = PublishPage(page, base_url)
        self.feed_page = FeedPage(page, base_url)

    def publish_search_like_and_comment(self, post: CommunityPostData) -> FeedPage:
        self.publish_page.open().fill(post).publish().expect_success()
        self.feed_page.open().search_for(post.title)
        self.feed_page.expect_post(post.title, post.content)
        self.feed_page.like(post.title)
        self.feed_page.comment(post.title, post.comment)
        return self.feed_page
