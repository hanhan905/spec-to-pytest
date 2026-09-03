"""Page object for the local community publish form."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, expect

from framework.data.models import CommunityPostData


class PublishPage:
    def __init__(self, page: Page, base_url: str) -> None:
        self.page = page
        self.base_url = base_url.rstrip("/")
        self.heading = page.get_by_role("heading", name="发布内容")
        self.title = page.get_by_label("标题")
        self.content = page.get_by_label("正文")
        self.tags = page.get_by_label("标签")
        self.image = page.get_by_label("图片")
        self.submit = page.get_by_role("button", name="发布")
        self.success = page.get_by_role("status")
        self.error = page.get_by_role("alert")

    def open(self) -> PublishPage:
        self.page.goto(f"{self.base_url}/publish")
        expect(self.heading).to_be_visible()
        return self

    def fill(self, post: CommunityPostData, image_path: Path | None = None) -> PublishPage:
        self.title.fill(post.title)
        self.content.fill(post.content)
        self.tags.fill(post.tags)
        if image_path is not None:
            self.image.set_input_files(image_path)
        return self

    def publish(self) -> PublishPage:
        self.submit.click()
        return self

    def expect_success(self) -> None:
        expect(self.success).to_have_text("内容发布成功！")
