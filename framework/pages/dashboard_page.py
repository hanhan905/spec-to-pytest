"""Dashboard page object composed with a reusable table component."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from framework.components.data_table import DataTable


class DashboardPage:
    def __init__(self, page: Page, base_url: str) -> None:
        self.page = page
        self.base_url = base_url.rstrip("/")
        self.heading = page.get_by_role("heading", name="自动化测试控制台")
        self.current_user = page.get_by_test_id("current-user")
        self.search = page.get_by_label("搜索")
        self.table = DataTable(page)

    def wait_until_loaded(self) -> DashboardPage:
        expect(self.page).to_have_url(f"{self.base_url}/dashboard")
        expect(self.heading).to_be_visible()
        expect(self.page.get_by_text("动态内容已加载")).to_be_visible()
        return self

    def search_for(self, text: str) -> None:
        self.search.fill(text)

    def sort_descending(self) -> None:
        self.page.get_by_role("button", name="名称降序").click()

    def open_details(self) -> None:
        self.page.get_by_role("button", name="打开详情").click()
        expect(self.page.get_by_role("dialog", name="详情弹窗")).to_be_visible()

    def expect_frame_ready(self) -> None:
        frame = self.page.frame_locator("iframe[title='嵌入状态']")
        expect(frame.get_by_test_id("frame-status")).to_have_text("Frame ready")
