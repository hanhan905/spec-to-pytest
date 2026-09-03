"""Explicit action-only repair points. These helpers never return observations."""

from typing import Any, cast

from playwright.sync_api import Locator, Page


def _locator(
    page: Page,
    *,
    role: str | None = None,
    name: str | None = None,
    label: str | None = None,
    test_id: str | None = None,
    css: str | None = None,
    exact: bool = True,
) -> Locator:
    if sum(value is not None for value in (role, label, test_id, css)) != 1:
        raise ValueError("Choose one action locator strategy")
    if role is not None:
        if name is None:
            raise ValueError("Role actions require a name")
        return page.get_by_role(cast(Any, role), name=name, exact=exact)
    if name is not None:
        raise ValueError("Name belongs only to role locators")
    if label is not None:
        return page.get_by_label(label, exact=exact)
    if test_id is not None:
        return page.get_by_test_id(test_id)
    assert css is not None
    return page.locator(css)


def _timeout(value: int) -> None:
    if type(value) is not int or not 100 <= value <= 30_000:
        raise ValueError("Action timeout must be 100..30000 milliseconds")


def click(page: Page, action_id: str, *, timeout: int = 5000, **locator: Any) -> None:
    _timeout(timeout)
    _locator(page, **locator).click(timeout=timeout)


def fill(page: Page, action_id: str, value: str, *, timeout: int = 5000, **locator: Any) -> None:
    _timeout(timeout)
    _locator(page, **locator).fill(value, timeout=timeout)


def wait_visible(page: Page, action_id: str, *, timeout: int = 5000, **locator: Any) -> None:
    _timeout(timeout)
    _locator(page, **locator).wait_for(state="visible", timeout=timeout)
