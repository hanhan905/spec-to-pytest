"""Never reuse or terminate an unrelated service just because /health returns 200."""

from __future__ import annotations

import errno
import os
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import BinaryIO, Literal
from urllib.parse import urlsplit
from uuid import uuid4

import httpx


def parse_local_url(value: str) -> tuple[str, int]:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost"}
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Only an exact loopback HTTP origin is supported")
    return value.rstrip("/"), parsed.port or 80


def assert_serial(arguments: list[str]) -> None:
    if any(arg.startswith(("-n", "--numprocesses", "--dist")) for arg in arguments):
        raise ValueError("v0.1 supports serial test runs only")


class OwnedApp:
    def __init__(
        self,
        base_url: str,
        data_dir: Path,
        log_path: Path,
        bug_mode: Literal["healthy", "comment_counter"] = "healthy",
    ) -> None:
        self.base_url, self.port = parse_local_url(base_url)
        self.data_dir, self.log_path, self.bug_mode = data_dir, log_path, bug_mode
        self.instance_id = uuid4().hex
        self.control_token = secrets.token_urlsafe(32)
        self.process: subprocess.Popen[bytes] | None = None
        self.log: BinaryIO | None = None

    def __enter__(self) -> OwnedApp:
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("127.0.0.1", self.port))
        except OSError as error:
            if error.errno != errno.EADDRINUSE:
                raise RuntimeError(
                    "Cannot bind the configured loopback port; check host permissions"
                ) from error
            raise RuntimeError(
                f"Configured port {self.port} is occupied; refusing to reuse it"
            ) from error
        finally:
            probe.close()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log = self.log_path.open("xb")
        environment = {
            **os.environ,
            "PRACTICE_DATA_DIR": str(self.data_dir.resolve()),
            "PRACTICE_ORIGIN": self.base_url,
            "PRACTICE_INSTANCE_ID": self.instance_id,
            "PRACTICE_BUG_MODE": self.bug_mode,
            "PRACTICE_TESTING": "true",
            "PRACTICE_CONTROL_TOKEN": self.control_token,
        }
        try:
            self.process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "practice_app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(self.port),
                    "--no-access-log",
                ],
                cwd=Path(__file__).resolve().parents[2],
                env=environment,
                stdout=self.log,
                stderr=subprocess.STDOUT,
            )
            deadline = time.monotonic() + 15
            with httpx.Client(trust_env=False, timeout=0.4) as client:
                while time.monotonic() < deadline:
                    if self.process.poll() is not None:
                        raise RuntimeError(
                            "Owned app exited before readiness; see local startup log"
                        )
                    try:
                        reply = client.get(self.base_url + "/health")
                        payload = reply.json()
                        if reply.status_code == 200:
                            if (
                                payload.get("application_id") != "spec-to-pytest"
                                or payload.get("instance_id") != self.instance_id
                                or payload.get("bug_mode") != self.bug_mode
                                or payload.get("version") != "0.1.0.dev0"
                            ):
                                raise RuntimeError(
                                    "Application identity mismatch; refusing to reuse service"
                                )
                            return self
                    except (httpx.HTTPError, ValueError):
                        pass
                    time.sleep(0.1)
            raise RuntimeError("Owned app readiness timed out")
        except BaseException:
            self.stop()
            raise

    def stop(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        if self.log is not None:
            self.log.close()

    def __exit__(self, *exc_info: object) -> None:
        self.stop()
