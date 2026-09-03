from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from practice_app.main import create_app
from practice_app.settings import AppSettings


@pytest.fixture
def app_settings(tmp_path: Path) -> AppSettings:
    return AppSettings(
        data_dir=tmp_path,
        origin="http://testserver",
        testing=True,
        control_token="synthetic-control-for-tests",
    )


@pytest.fixture
def local_client(app_settings: AppSettings) -> Iterator[TestClient]:
    with TestClient(create_app(app_settings)) as client:
        yield client
