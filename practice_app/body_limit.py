"""Bound request streams as well as Content-Length declarations before multipart parsing."""

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class BodyLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        size = 0
        messages: list[Message] = []
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] == "http.request":
                size += len(message.get("body", b""))
                if size > self.max_bytes:
                    response = JSONResponse(
                        {"detail": "Request body is too large"},
                        status_code=413,
                        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
                    )
                    await response(scope, receive, send)
                    return
                messages.append(message)
                if not message.get("more_body", False):
                    break

        buffered = iter(messages)

        async def limited_receive() -> Message:
            message = next(buffered, None)
            return message if message is not None else await receive()

        await self.app(scope, limited_receive, send)
