from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from practice_app.main import create_app
from practice_app.settings import AppSettings


def make_image() -> bytes:
    stream = BytesIO()
    Image.new("RGB", (16, 12), "navy").save(stream, "PNG")
    return stream.getvalue()


def settings_for(tmp_path: Path, **changes: object) -> AppSettings:
    return AppSettings(
        data_dir=tmp_path,
        origin="http://testserver",
        testing=True,
        control_token="synthetic-control-for-tests",
        **changes,
    )


def login(client: TestClient) -> None:
    assert (
        client.post("/api/login", json={"username": "admin", "password": "admin123"}).status_code
        == 200
    )


def test_cookie_cannot_impersonate_a_user_and_logout_revokes_session(tmp_path: Path) -> None:
    with TestClient(create_app(settings_for(tmp_path))) as client:
        client.cookies.set("practice_session", "admin")
        assert client.get("/api/profile").status_code == 401
        client.cookies.clear()
        login(client)
        token = client.cookies.get("practice_session")
        assert token and token != "admin"
        assert client.post("/api/logout").status_code == 204
        client.cookies.set("practice_session", token)
        assert client.get("/api/profile").status_code == 401


def test_foreign_origin_is_rejected_without_writing_data(tmp_path: Path) -> None:
    with TestClient(create_app(settings_for(tmp_path))) as client:
        login(client)
        response = client.post(
            "/api/posts",
            data={"title": "x", "content": "y"},
            headers={"Origin": "https://untrusted.invalid"},
        )
        assert response.status_code == 403
        assert client.get("/api/posts").json()["total"] == 0


def test_reset_requires_test_mode_and_matching_control_token(tmp_path: Path) -> None:
    with TestClient(create_app(settings_for(tmp_path / "test"))) as client:
        assert client.post("/api/reset").status_code == 403
        assert client.post("/api/reset", headers={"X-Practice-Control": "wrong"}).status_code == 403
        assert (
            client.post(
                "/api/reset", headers={"X-Practice-Control": "synthetic-control-for-tests"}
            ).status_code
            == 204
        )
    with TestClient(
        create_app(AppSettings(data_dir=tmp_path / "manual", origin="http://testserver"))
    ) as client:
        assert client.post("/api/reset").status_code == 404


def test_real_image_and_content_survive_restart_without_session_reuse(tmp_path: Path) -> None:
    config = settings_for(tmp_path)
    with TestClient(create_app(config)) as client:
        login(client)
        old_session = client.cookies.get("practice_session")
        response = client.post(
            "/api/posts",
            data={"title": "real image", "content": "stored"},
            files={"image": ("../../private.png", make_image(), "image/png")},
        )
        assert response.status_code == 201
        post = response.json()
        image_url = post["image_url"]
        image = client.get(image_url)
        assert Image.open(BytesIO(image.content)).size == (16, 12)
        assert "private" not in post["image_name"]
    with TestClient(create_app(config)) as restarted:
        restarted.cookies.set("practice_session", old_session)
        assert restarted.get("/api/profile").status_code == 401
        restarted.cookies.clear()
        login(restarted)
        assert restarted.get("/api/posts").json()["total"] == 1
        assert restarted.get(image_url).status_code == 200


@pytest.mark.parametrize(
    "content,mime",
    [
        (b"not an image", "image/png"),
        (b"GIF89a", "image/gif"),
        (make_image(), "image/jpeg"),
        (b"x" * (2 * 1024 * 1024 + 1), "image/png"),
    ],
    ids=["corrupt", "gif", "mismatched-mime", "over-2mib"],
)
def test_bad_images_leave_no_posts_or_media(tmp_path: Path, content: bytes, mime: str) -> None:
    with TestClient(create_app(settings_for(tmp_path))) as client:
        login(client)
        response = client.post(
            "/api/posts",
            data={"title": "bad image", "content": "must reject"},
            files={"image": ("anything.png", content, mime)},
        )
        assert response.status_code == 422
        assert client.get("/api/posts").json()["total"] == 0
        assert list((tmp_path / "media").iterdir()) == []


def test_data_reset_cannot_clear_another_instance(tmp_path: Path) -> None:
    with (
        TestClient(create_app(settings_for(tmp_path / "first"))) as first,
        TestClient(create_app(settings_for(tmp_path / "second"))) as second,
    ):
        for client in (first, second):
            login(client)
            assert (
                client.post(
                    "/api/posts", data={"title": "independent", "content": "data"}
                ).status_code
                == 201
            )
        assert (
            first.post(
                "/api/reset", headers={"X-Practice-Control": "synthetic-control-for-tests"}
            ).status_code
            == 204
        )
        assert first.get("/api/posts").json()["total"] == 0
        assert second.get("/api/posts").json()["total"] == 1


def test_rules_trim_before_checking_maximum_length(tmp_path: Path) -> None:
    with TestClient(create_app(settings_for(tmp_path))) as client:
        login(client)
        response = client.post(
            "/api/posts", data={"title": " " + "a" * 50 + " ", "content": " valid "}
        )
        assert response.status_code == 201
        assert response.json()["title"] == "a" * 50


def test_chunked_body_cannot_bypass_the_request_limit(tmp_path: Path) -> None:
    with TestClient(create_app(settings_for(tmp_path))) as client:
        login(client)
        chunks = (b"x" * 65536 for _ in range(34))
        response = client.post(
            "/api/posts",
            content=chunks,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 413
        assert client.get("/api/posts").json()["total"] == 0


def test_unicode_password_is_rejected_not_a_server_error(tmp_path: Path) -> None:
    with TestClient(create_app(settings_for(tmp_path))) as client:
        response = client.post("/api/login", json={"username": "admin", "password": "错误密码"})
        assert response.status_code == 401


def test_media_metadata_removed_and_reset_deletes_only_owned_image(tmp_path: Path) -> None:
    raw = BytesIO()
    photo = Image.new("RGB", (24, 16), "teal")
    exif = photo.getexif()
    exif[270] = "synthetic private metadata"
    photo.save(raw, "JPEG", exif=exif)
    with TestClient(create_app(settings_for(tmp_path))) as client:
        login(client)
        response = client.post(
            "/api/posts",
            data={"title": "metadata", "content": "check"},
            files={"image": ("photo.jpg", raw.getvalue(), "image/jpeg")},
        )
        assert response.status_code == 201
        image = client.get(response.json()["image_url"])
        assert not Image.open(BytesIO(image.content)).getexif()
        assert (
            client.post(
                "/api/reset", headers={"X-Practice-Control": "synthetic-control-for-tests"}
            ).status_code
            == 204
        )
        assert client.get(response.json()["image_url"]).status_code == 404
        assert list((tmp_path / "media").iterdir()) == []


def test_pixel_budget_checked_before_decode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from practice_app import media

    assert media.MAX_IMAGE_PIXELS == 20_000_000
    monkeypatch.setattr(media, "MAX_IMAGE_PIXELS", 100)
    with TestClient(create_app(settings_for(tmp_path))) as client:
        login(client)
        response = client.post(
            "/api/posts",
            data={"title": "pixels", "content": "check"},
            files={"image": ("photo.png", make_image(), "image/png")},
        )
        assert response.status_code == 422
        assert list((tmp_path / "media").iterdir()) == []
