"""A workflow coordinates page objects without turning tests into click scripts."""

from playwright.sync_api import Page

from framework.data.models import Credentials
from framework.pages.dashboard_page import DashboardPage
from framework.pages.login_page import LoginPage


class AuthWorkflow:
    def __init__(self, page: Page, base_url: str) -> None:
        self.login_page = LoginPage(page, base_url)
        self.dashboard_page = DashboardPage(page, base_url)

    def login(self, credentials: Credentials) -> DashboardPage:
        self.login_page.open().login_as(credentials)
        return self.dashboard_page.wait_until_loaded()
