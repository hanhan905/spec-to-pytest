"""Pytest command-line configuration and typed settings fixture."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from framework.config.settings import Settings, settings_with_overrides
from framework.runtime.service import OwnedApp, assert_serial


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("automation framework")
    group.addoption("--environment", default=None, help="Named local configuration environment")
    group.addoption("--app-url", default=None, help="Override the practice application URL")
    group.addoption("--reverse-order", action="store_true", help="Verify order independence")


def pytest_configure(config: pytest.Config) -> None:
    assert_serial(list(config.invocation_params.args))


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--reverse-order"):
        items.reverse()


@pytest.fixture(scope="session")
def settings(
    pytestconfig: pytest.Config, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Settings]:
    app_url = pytestconfig.getoption("--app-url")
    base = settings_with_overrides(
        environment=pytestconfig.getoption("--environment"),
        base_url=app_url,
        api_url=app_url,
    )
    if base.instance_id and base.control_token.get_secret_value():
        yield base
        return
    root = tmp_path_factory.mktemp("practice-service")
    with OwnedApp(base.base_url, root / "data", root / "app.log") as service:
        yield settings_with_overrides(
            base_url=service.base_url,
            api_url=service.base_url,
            control_token=service.control_token,
            instance_id=service.instance_id,
        )
