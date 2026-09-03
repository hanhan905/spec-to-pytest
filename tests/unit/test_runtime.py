import socket
from pathlib import Path

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
