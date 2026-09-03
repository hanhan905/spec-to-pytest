"""Component object for the reusable data table on the practice dashboard."""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect


class DataTable:
    def __init__(self, page: Page) -> None:
        self.table = page.get_by_role("table", name="项目表格")
        self.rows = self.table.get_by_role("row")

    def data_rows(self) -> Locator:
        return self.table.locator("tbody tr")

    def expect_row_count(self, count: int) -> None:
        expect(self.data_rows()).to_have_count(count)

    def expect_contains(self, text: str) -> None:
        expect(self.table).to_contain_text(text)

    def names(self) -> list[str]:
        return self.table.locator("tbody tr td:nth-child(2)").all_text_contents()
