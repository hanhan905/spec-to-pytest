from fastapi.testclient import TestClient


def test_health(local_client: TestClient) -> None:
    client = local_client
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["application_id"] == "spec-to-pytest"


def test_login_and_list_items(local_client: TestClient) -> None:
    client = local_client
    login = client.post("/api/login", json={"username": "admin", "password": "admin123"})
    assert login.status_code == 200

    items = client.get("/api/items", params={"q": "a", "sort": "asc", "page_size": 50})
    assert items.status_code == 200
    payload = items.json()
    assert payload["total"] == 5
    assert payload["items"][0]["name"] == "Alpha"


def test_rejects_invalid_login(local_client: TestClient) -> None:
    client = local_client
    response = client.post("/api/login", json={"username": "admin", "password": "wrong"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"
