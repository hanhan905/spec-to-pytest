import pytest

from framework.api.practice_client import PracticeApiClient
from framework.config.settings import Settings
from framework.data.factories import admin_credentials, invalid_credentials


@pytest.mark.api
@pytest.mark.smoke
def test_health_endpoint(settings: Settings) -> None:
    with PracticeApiClient(settings.api_url) as client:
        response = client.health()
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["application_id"] == "spec-to-pytest"


@pytest.mark.api
@pytest.mark.regression
def test_login_profile_and_items(settings: Settings) -> None:
    with PracticeApiClient(settings.api_url) as client:
        assert client.login(admin_credentials()).status_code == 200
        profile = client.profile()
        items = client.items(q="a", sort="desc", page_size=50)

    assert profile.json() == {"username": "admin", "role": "admin"}
    assert items.status_code == 200
    assert items.json()["items"][0]["name"] == "Zeta"


@pytest.mark.api
@pytest.mark.regression
def test_invalid_login_is_rejected(settings: Settings) -> None:
    with PracticeApiClient(settings.api_url) as client:
        response = client.login(invalid_credentials())
    assert response.status_code == 401


@pytest.mark.api
@pytest.mark.regression
def test_content_api_lifecycle(settings: Settings) -> None:
    with PracticeApiClient(settings.api_url, control_token=settings.control_token) as client:
        assert client.login(admin_credentials()).status_code == 200
        assert client.reset().status_code == 204
        created = client.create_post(
            {
                "title": "API生成内容",
                "content": "验证发布、搜索、点赞和评论接口。",
                "tags": "API测试, AI测试",
            }
        )
        post_id = created.json()["id"]
        search = client.posts(q="AI测试")
        like = client.toggle_like(post_id)
        comment = client.add_comment(post_id, "接口评论成功")

    assert created.status_code == 201
    assert search.json()["total"] == 1
    assert like.json()["like_count"] == 1
    assert comment.json()["comment_count"] == 1
