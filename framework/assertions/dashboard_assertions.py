"""Domain-oriented assertions produce intent-revealing failures."""

from playwright.sync_api import expect

from framework.pages.dashboard_page import DashboardPage


def expect_logged_in_user(dashboard: DashboardPage, username: str) -> None:
    expect(dashboard.current_user).to_have_text(username)


def expect_item_names(dashboard: DashboardPage, expected: list[str]) -> None:
    name_cells = dashboard.table.table.locator("tbody tr td:nth-child(2)")
    expect(name_cells).to_have_text(expected)
