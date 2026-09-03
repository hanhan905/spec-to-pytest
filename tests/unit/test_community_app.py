from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from practice_app.main import create_app
from practice_app.settings import AppSettings


@pytest.fixture
def community_client(app_settings: AppSettings) -> Iterator[TestClient]:
    with TestClient(create_app(app_settings)) as client:
        login = client.post(
            "/api/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert login.status_code == 200
        yield client


def create_post(client: TestClient, **overrides: str) -> dict[str, object]:
    data = {
        "title": "我的AI测试实践",
        "content": "用 Playwright MCP 生成可执行测试，并保留完整证据。",
        "tags": "AI测试, Playwright, AI测试",
        **overrides,
    }
    response = client.post("/api/posts", data=data)
    assert response.status_code == 201
    return response.json()


def test_community_pages_require_login(local_client: TestClient) -> None:
    assert local_client.get("/feed", follow_redirects=False).status_code == 302
    assert local_client.get("/publish", follow_redirects=False).status_code == 302


def test_content_lifecycle(community_client: TestClient) -> None:
    post = create_post(community_client)
    assert post["tags"] == ["AI测试", "Playwright"]

    search = community_client.get("/api/posts", params={"q": "playwright"})
    assert search.status_code == 200
    assert search.json()["total"] == 1
    assert search.json()["posts"][0]["title"] == "我的AI测试实践"

    like = community_client.post(f"/api/posts/{post['id']}/like")
    assert like.json() == {"post_id": post["id"], "liked": True, "like_count": 1}
    unlike = community_client.post(f"/api/posts/{post['id']}/like")
    assert unlike.json() == {"post_id": post["id"], "liked": False, "like_count": 0}

    comment = community_client.post(
        f"/api/posts/{post['id']}/comments",
        json={"text": "这是自动生成后的验证评论"},
    )
    assert comment.status_code == 201
    assert comment.json()["comment_count"] == 1

    refreshed = community_client.get("/api/posts").json()["posts"][0]
    assert refreshed["comment_count"] == 1
    assert refreshed["comments"][0]["text"] == "这是自动生成后的验证评论"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", "   "),
        ("content", "   "),
        ("title", "题" * 51),
        ("content", "文" * 501),
    ],
)
def test_post_validation_rejects_invalid_text(
    community_client: TestClient,
    field: str,
    value: str,
) -> None:
    data = {"title": "有效标题", "content": "有效正文", field: value}
    response = community_client.post("/api/posts", data=data)
    assert response.status_code == 422


def test_post_rejects_invalid_or_oversized_image(community_client: TestClient) -> None:
    invalid_type = community_client.post(
        "/api/posts",
        data={"title": "图片类型", "content": "验证图片类型"},
        files={"image": ("sample.gif", b"GIF89a", "image/gif")},
    )
    assert invalid_type.status_code == 422
    assert invalid_type.json()["detail"] == "Only PNG and JPG images are supported"

    oversized = community_client.post(
        "/api/posts",
        data={"title": "图片大小", "content": "验证图片大小"},
        files={"image": ("large.png", b"0" * (2 * 1024 * 1024 + 1), "image/png")},
    )
    assert oversized.status_code == 422
    assert oversized.json()["detail"] == "Image must not exceed 2 MB"


def test_comment_rejects_blank_and_overlong_text(community_client: TestClient) -> None:
    post = create_post(community_client)
    blank = community_client.post(
        f"/api/posts/{post['id']}/comments",
        json={"text": "   "},
    )
    overlong = community_client.post(
        f"/api/posts/{post['id']}/comments",
        json={"text": "评" * 101},
    )
    assert blank.status_code == 422
    assert overlong.status_code == 422


def test_comment_counter_bug_mode_preserves_the_defect(
    app_settings: AppSettings,
) -> None:
    app_settings.bug_mode = "comment_counter"
    with TestClient(create_app(app_settings)) as client:
        assert (
            client.post(
                "/api/login", json={"username": "admin", "password": "admin123"}
            ).status_code
            == 200
        )
        post = create_post(client)
        response = client.post(
            f"/api/posts/{post['id']}/comments", json={"text": "评论已保存但计数故意不更新"}
        )
        assert response.status_code == 201
        assert response.json()["comment_count"] == 0
        refreshed = client.get("/api/posts").json()["posts"][0]
        assert len(refreshed["comments"]) == 1
        assert refreshed["comment_count"] == 0
