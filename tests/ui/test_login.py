import allure
import pytest
from playwright.sync_api import Page

from framework.assertions.dashboard_assertions import expect_logged_in_user
from framework.config.settings import Settings
from framework.data.factories import admin_credentials, invalid_credentials
from framework.pages.login_page import LoginPage
from framework.workflows.auth_workflow import AuthWorkflow


@allure.epic("Practice application")
@allure.feature("Authentication")
@allure.story("Successful login")
@pytest.mark.ui
@pytest.mark.smoke
def test_admin_can_log_in(configured_page: Page, settings: Settings) -> None:
    with allure.step("Log in as the administrator"):
        dashboard = AuthWorkflow(configured_page, settings.base_url).login(admin_credentials())
    with allure.step("Verify the authenticated identity"):
        expect_logged_in_user(dashboard, "admin")


@allure.epic("Practice application")
@allure.feature("Authentication")
@allure.story("Invalid credentials")
@pytest.mark.ui
@pytest.mark.regression
def test_invalid_credentials_show_error(configured_page: Page, settings: Settings) -> None:
    login = LoginPage(configured_page, settings.base_url).open()
    login.login_as(invalid_credentials())
    login.expect_error("Invalid username or password")
