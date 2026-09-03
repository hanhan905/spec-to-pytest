"""Adapted historical TRAE test (maintainer review pending) for image type and size API rejection.

scenario_id: content_lifecycle
case_id: CONTENT_007
original_run_id: 20260821T163455Z-content_lifecycle-8aafd9
"""

from __future__ import annotations

import allure
import pytest

from framework.api.practice_client import PracticeApiClient
from framework.config.settings import Settings
from framework.data.factories import admin_credentials

MAX_IMAGE_BYTES = 2 * 1024 * 1024


@allure.epic("AI-generated testing demo")
@allure.feature("Local content community")
@allure.story("Image type and size rejection")
@allure.title("CONTENT_007 不支持的图片类型和超大图片通过发布接口被拒绝")
@pytest.mark.case_id("CONTENT_007")
@pytest.mark.generated
@pytest.mark.ai_demo
def test_image_type_and_size_rejected_by_api(settings: Settings) -> None:
    with allure.step("Reset local community data via an authenticated API client"):
        client = PracticeApiClient(settings.api_url, control_token=settings.control_token)
        try:
            client.login(admin_credentials())
            assert client.reset().status_code == 204

            with allure.step("Upload a GIF image and expect a type rejection"):
                gif_response = client.create_post(
                    {"title": "图片边界", "content": "正文"},
                    files={"image": ("bad.gif", b"GIF89a", "image/gif")},
                )
                assert gif_response.status_code == 422
                assert gif_response.json()["detail"] == "Only PNG and JPG images are supported"

            with allure.step("Upload an oversized PNG image and expect a size rejection"):
                oversized = b"\x89PNG\r\n\x1a\n" + b"\x00" * (MAX_IMAGE_BYTES + 1)
                assert len(oversized) > MAX_IMAGE_BYTES
                png_response = client.create_post(
                    {"title": "图片边界", "content": "正文"},
                    files={"image": ("big.png", oversized, "image/png")},
                )
                assert png_response.status_code == 422
                assert png_response.json()["detail"] == "Image must not exceed 2 MB"

            with allure.step("Verify no content was created"):
                assert client.posts().json()["total"] == 0
        finally:
            client.close()
