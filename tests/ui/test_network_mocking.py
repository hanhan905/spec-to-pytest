import pytest
from playwright.sync_api import Page

from framework.config.settings import Settings
from framework.data.factories import admin_credentials
from framework.mocks.routes import append_item_to_real_response, mock_items
from framework.workflows.auth_workflow import AuthWorkflow


@pytest.mark.ui
@pytest.mark.regression
def test_route_can_replace_api_response(configured_page: Page, settings: Settings) -> None:
    mock_items(
        configured_page,
        [{"id": 99, "name": "Mock Alpha", "category": "Web", "status": "Active"}],
    )
    dashboard = AuthWorkflow(configured_page, settings.base_url).login(admin_credentials())
    dashboard.table.expect_row_count(1)
    dashboard.table.expect_contains("Mock Alpha")


@pytest.mark.ui
@pytest.mark.regression
def test_route_can_patch_real_response(configured_page: Page, settings: Settings) -> None:
    append_item_to_real_response(
        configured_page,
        {"id": 100, "name": "Injected", "category": "Mock", "status": "Active"},
    )
    dashboard = AuthWorkflow(configured_page, settings.base_url).login(admin_credentials())
    dashboard.table.expect_contains("Injected")
