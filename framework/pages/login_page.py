"""Login page object: selectors plus user-visible page actions."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from framework.data.models import Credentials


class LoginPage:
    def __init__(self, page: Page, base_url: str) -> None:
        self.page = page
        self.base_url = base_url.rstrip("/")
        self.username = page.get_by_label("用户名")
        self.password = page.get_by_label("密码")
        self.submit = page.get_by_role("button", name="登录")
        self.error = page.get_by_role("alert")

    def open(self) -> LoginPage:
        self.page.goto(f"{self.base_url}/login")
        expect(self.page).to_have_title("登录 - Playwright Test Lab")
        return self

    def login_as(self, credentials: Credentials) -> None:
        self.username.fill(credentials.username)
        self.password.fill(credentials.password)
        self.submit.click()

    def expect_error(self, message: str) -> None:
        expect(self.error).to_have_text(message)
