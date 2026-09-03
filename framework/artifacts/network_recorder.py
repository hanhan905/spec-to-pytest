"""Record lightweight response metadata without storing sensitive bodies."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from urllib.parse import urlsplit, urlunsplit

from playwright.sync_api import Page, Response


@dataclass(frozen=True, slots=True)
class ResponseEvent:
    method: str
    status: int
    url: str


class NetworkRecorder:
    def __init__(self, page: Page) -> None:
        self.events: list[ResponseEvent] = []
        page.on("response", self._record)

    def _record(self, response: Response) -> None:
        self.events.append(
            ResponseEvent(
                method=response.request.method,
                status=response.status,
                url=urlunsplit(
                    (
                        urlsplit(response.url).scheme,
                        urlsplit(response.url).netloc.split("@")[-1],
                        urlsplit(response.url).path,
                        "",
                        "",
                    )
                ),
            )
        )

    def serializable(self) -> list[dict[str, str | int]]:
        return [asdict(event) for event in self.events]
