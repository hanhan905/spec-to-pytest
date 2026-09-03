"""Adapted historical TRAE test (maintainer review pending) for the over-length title API rejection.

scenario_id: content_lifecycle
case_id: CONTENT_005
original_run_id: 20260821T163455Z-content_lifecycle-8aafd9
"""

from __future__ import annotations

import allure
import pytest

from framework.api.practice_client import PracticeApiClient
from framework.config.settings import Settings
from framework.data.content import load_row
from framework.data.factories import admin_credentials


@allure.epic("AI-generated testing demo")
@allure.feature("Local content community")
@allure.story("Over-length title API rejection")
@allure.title("CONTENT_005 标题超过 50 个字符通过发布接口返回 422 且不创建内容")
@pytest.mark.case_id("CONTENT_005")
@pytest.mark.generated
@pytest.mark.ai_demo
def test_overlength_title_rejected_by_api(settings: Settings) -> None:
    with allure.step("Reset local community data via an authenticated API client"):
        client = PracticeApiClient(settings.api_url, control_token=settings.control_token)
        try:
            client.login(admin_credentials())
            assert client.reset().status_code == 204

            overlong_title = load_row("TITLE_OVER_051")["title"]
            assert len(overlong_title) == 51

            with allure.step("Submit a 51-character title to the publish API"):
                response = client.create_post({"title": overlong_title, "content": "正文"})

            with allure.step("Verify the API rejects the over-length title"):
                assert response.status_code == 422

            with allure.step("Verify no content was created"):
                assert client.posts().json()["total"] == 0
        finally:
            client.close()
