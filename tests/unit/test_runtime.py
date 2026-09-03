import socket
from pathlib import Path

import httpx
import pytest

from framework.runtime.service import OwnedApp, assert_serial, parse_local_url


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:8000",
        "http://example.com",
        "http://localhost:8000/path",
        "http://user:pass@localhost:8000",
        "http://localhost:8000?key=secret",
    ],
)
def test_rejects_nonlocal_or_ambiguous_origins(url: str) -> None:
    with pytest.raises(ValueError, match="loopback"):
        parse_local_url(url)


@pytest.mark.parametrize("args", [["-n", "2"], ["-n2"], ["--numprocesses=2"], ["--dist=load"]])
def test_parallel_execution_is_explicitly_rejected(args: list[str]) -> None:
    with pytest.raises(ValueError, match="serial"):
        assert_serial(args)


def test_occupied_port_is_not_reused_or_killed(tmp_path: Path) -> None:
    with socket.socket() as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen()
        port = occupied.getsockname()[1]
        with (
            pytest.raises(RuntimeError, match="occupied"),
            OwnedApp(f"http://127.0.0.1:{port}", tmp_path / "data", tmp_path / "log"),
        ):
            pass
        assert occupied.getsockname()[1] == port
        assert not (tmp_path / "data").exists()


def test_owned_service_restarts_with_persistent_data_but_new_sessions(tmp_path: Path) -> None:
    with socket.socket() as port_probe:
        port_probe.bind(("127.0.0.1", 0))
        port = port_probe.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    with httpx.Client(base_url=origin, trust_env=False) as client:
        with OwnedApp(origin, tmp_path / "data", tmp_path / "first.log") as first:
            assert (
                client.post(
                    "/api/login", json={"username": "admin", "password": "admin123"}
                ).status_code
                == 200
            )
            assert (
                client.post(
                    "/api/posts", data={"title": "restart", "content": "retained"}
                ).status_code
                == 201
            )
            first_id = client.get("/health").json()["instance_id"]
        assert first.process is not None and first.process.poll() is not None
        with OwnedApp(origin, tmp_path / "data", tmp_path / "second.log"):
            assert client.get("/api/profile").status_code == 401
            assert (
                client.post(
                    "/api/login", json={"username": "admin", "password": "admin123"}
                ).status_code
                == 200
            )
            assert client.get("/api/posts").json()["total"] == 1
            assert client.get("/health").json()["instance_id"] != first_id
