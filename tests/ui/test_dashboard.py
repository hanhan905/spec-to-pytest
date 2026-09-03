import pytest
from playwright.sync_api import BrowserContext, Page

from framework.assertions.dashboard_assertions import expect_item_names, expect_logged_in_user
from framework.config.settings import Settings
from framework.pages.dashboard_page import DashboardPage


@pytest.mark.ui
@pytest.mark.smoke
def test_dashboard_search(authenticated_page: Page, settings: Settings) -> None:
    dashboard = DashboardPage(authenticated_page, settings.base_url)
    dashboard.search_for("Delta")
    dashboard.table.expect_row_count(1)
    dashboard.table.expect_contains("Delta")


@pytest.mark.ui
@pytest.mark.regression
def test_dashboard_sort_dialog_and_frame(authenticated_page: Page, settings: Settings) -> None:
    dashboard = DashboardPage(authenticated_page, settings.base_url)
    dashboard.sort_descending()
    expect_item_names(dashboard, ["Zeta", "Gamma", "Epsilon", "Delta", "Beta", "Alpha"])
    dashboard.open_details()
    dashboard.expect_frame_ready()


@pytest.mark.ui
@pytest.mark.regression
def test_storage_state_can_seed_isolated_context(
    isolated_authenticated_context: BrowserContext, settings: Settings
) -> None:
    page = isolated_authenticated_context.new_page()
    page.goto("/dashboard")
    dashboard = DashboardPage(page, settings.base_url).wait_until_loaded()
    expect_logged_in_user(dashboard, "admin")
