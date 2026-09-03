"""Page object for content search, likes, and comments."""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect


class FeedPage:
    def __init__(self, page: Page, base_url: str) -> None:
        self.page = page
        self.base_url = base_url.rstrip("/")
        self.heading = page.get_by_role("heading", name="内容广场")
        self.search = page.get_by_label("搜索标题、正文或标签")

    def open(self) -> FeedPage:
        self.page.goto(f"{self.base_url}/feed")
        expect(self.heading).to_be_visible()
        return self

    def search_for(self, query: str) -> FeedPage:
        self.search.fill(query)
        self.page.get_by_role("button", name="搜索").click()
        return self

    def post(self, title: str) -> Locator:
        heading = self.page.get_by_role("heading", name=title)
        return self.page.get_by_role("article").filter(has=heading)

    def expect_post(self, title: str, content: str) -> Locator:
        card = self.post(title)
        expect(card).to_be_visible()
        expect(card.get_by_text(content)).to_be_visible()
        return card

    def like(self, title: str) -> None:
        button = self.page.get_by_role("button", name=f"点赞：{title}")
        button.click()
        expect(button).to_have_attribute("aria-pressed", "true")
        expect(button).to_have_text("点赞 1")

    def comment(self, title: str, text: str) -> None:
        card = self.post(title)
        card.get_by_label(f"评论内容：{title}").fill(text)
        card.get_by_role("button", name="提交评论").click()
        expect(card.get_by_text(text)).to_be_visible()
        expect(card.get_by_text("评论 1", exact=True)).to_be_visible()
