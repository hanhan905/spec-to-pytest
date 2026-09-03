"""Local-only practice application with isolated storage and explicit test controls."""

from __future__ import annotations

import asyncio
import hmac
import secrets
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Annotated, Literal, cast

from fastapi import APIRouter, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import RequestResponseEndpoint

from practice_app.body_limit import BodyLimitMiddleware
from practice_app.media import MAX_IMAGE_BYTES, MediaStore
from practice_app.models import (
    CommentRequest,
    CommentResponse,
    ItemsResponse,
    LikeResponse,
    LoginRequest,
    PostsResponse,
    PostView,
    UploadResponse,
    UserView,
)
from practice_app.repository import Repository
from practice_app.settings import AppSettings
from practice_app.state import ITEMS, USERS

SESSION_COOKIE = "practice_session"
VERSION = "0.1.0.dev0"
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
router = APIRouter()


@dataclass
class AppContext:
    settings: AppSettings
    repository: Repository
    media: MediaStore
    sessions: dict[str, tuple[str, float]] = field(default_factory=dict)
    session_lock: Lock = field(default_factory=Lock)


def context(request: Request) -> AppContext:
    return cast(AppContext, request.app.state.context)


def current_user(request: Request) -> UserView:
    state = context(request)
    with state.session_lock:
        record = state.sessions.get(request.cookies.get(SESSION_COOKIE, ""))
        if record is None or record[1] <= time.monotonic():
            raise HTTPException(401, "Not authenticated")
    return UserView(username=record[0], role=str(USERS[record[0]]["role"]))


def create_app(settings: AppSettings | None = None) -> FastAPI:
    config = settings or AppSettings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.context = AppContext(
            config, Repository(config.data_dir), MediaStore(config.data_dir)
        )
        yield
        application.state.context.sessions.clear()

    application = FastAPI(
        title="spec-to-pytest local practice app", version=VERSION, lifespan=lifespan
    )

    @application.middleware("http")
    async def local_requests(request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if (origin is not None and origin != config.origin) or request.headers.get(
                "sec-fetch-site"
            ) == "cross-site":
                return JSONResponse({"detail": "Foreign origin is not allowed"}, status_code=403)
            length = request.headers.get("content-length")
            if length and (not length.isdecimal() or int(length) > MAX_IMAGE_BYTES + 65536):
                return JSONResponse({"detail": "Request body is too large"}, status_code=413)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    application.mount(
        "/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static"
    )
    application.include_router(router)
    application.add_middleware(BodyLimitMiddleware, max_bytes=MAX_IMAGE_BYTES + 65536)
    return application


@router.get("/health")
def health(request: Request) -> dict[str, str]:
    config = context(request).settings
    return {
        "status": "ok",
        "application_id": "spec-to-pytest",
        "version": VERSION,
        "instance_id": config.instance_id,
        "bug_mode": config.bug_mode,
    }


@router.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse("/login", status_code=302)


@router.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="login.html")


def protected_page(request: Request, name: str) -> HTMLResponse | RedirectResponse:
    try:
        user = current_user(request)
    except HTTPException:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse(
        request=request, name=f"{name}.html", context={"user": user, "active_page": name}
    )


@router.get("/dashboard", response_model=None, include_in_schema=False)
def dashboard_page(request: Request) -> HTMLResponse | RedirectResponse:
    return protected_page(request, "dashboard")


@router.get("/feed", response_model=None, include_in_schema=False)
def feed_page(request: Request) -> HTMLResponse | RedirectResponse:
    return protected_page(request, "feed")


@router.get("/publish", response_model=None, include_in_schema=False)
def publish_page(request: Request) -> HTMLResponse | RedirectResponse:
    return protected_page(request, "publish")


@router.get("/frame", response_class=HTMLResponse, include_in_schema=False)
def frame_page() -> HTMLResponse:
    return HTMLResponse(
        "<main><h2>Embedded status</h2><p data-testid='frame-status'>Frame ready</p></main>"
    )


@router.post("/api/login", response_model=UserView)
def login(request: Request, payload: LoginRequest) -> JSONResponse:
    user = USERS.get(payload.username)
    if user is None or not hmac.compare_digest(
        str(user["password"]).encode(), payload.password.encode()
    ):
        raise HTTPException(401, "Invalid username or password")
    state = context(request)
    token = secrets.token_urlsafe(32)
    with state.session_lock:
        now = time.monotonic()
        state.sessions = {key: value for key, value in state.sessions.items() if value[1] > now}
        state.sessions.pop(request.cookies.get(SESSION_COOKIE, ""), None)
        state.sessions[token] = (payload.username, now + state.settings.session_seconds)
    response = JSONResponse({"username": payload.username, "role": user["role"]})
    response.set_cookie(
        SESSION_COOKIE, token, httponly=True, samesite="lax", max_age=state.settings.session_seconds
    )
    return response


@router.post("/api/logout", status_code=204)
def logout(request: Request) -> Response:
    state = context(request)
    with state.session_lock:
        state.sessions.pop(request.cookies.get(SESSION_COOKIE, ""), None)
    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE)
    return response


@router.get("/api/profile", response_model=UserView)
def profile(request: Request) -> UserView:
    return current_user(request)


@router.get("/api/items", response_model=ItemsResponse)
def list_items(
    request: Request,
    q: str = "",
    sort: Literal["asc", "desc"] = "asc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 3,
) -> ItemsResponse:
    current_user(request)
    ordered = sorted(
        [item for item in ITEMS if q.lower() in item.name.lower()],
        key=lambda item: item.name,
        reverse=sort == "desc",
    )
    start = (page - 1) * page_size
    return ItemsResponse(
        items=ordered[start : start + page_size], total=len(ordered), page=page, page_size=page_size
    )


@router.get("/api/posts", response_model=PostsResponse)
def list_posts(request: Request, q: str = "") -> PostsResponse:
    posts = context(request).repository.posts(current_user(request).username, q)
    return PostsResponse(posts=posts, total=len(posts))


def clean_text(value: str, label: str, maximum: int) -> str:
    clean = value.strip()
    if not clean:
        raise HTTPException(422, f"{label} must not be blank")
    if len(clean) > maximum:
        raise HTTPException(422, f"{label} must not exceed {maximum} characters")
    return clean


@router.post("/api/posts", response_model=PostView, status_code=201)
async def create_post(
    request: Request,
    title: Annotated[str, Form()],
    content: Annotated[str, Form()],
    tags: Annotated[str, Form()] = "",
    image: Annotated[UploadFile | None, File()] = None,
) -> PostView:
    user = current_user(request)
    state = context(request)
    clean_title, clean_content = clean_text(title, "Title", 50), clean_text(content, "Content", 500)
    parsed_tags = list(dict.fromkeys(tag.strip() for tag in tags.split(",") if tag.strip()))
    name = await state.media.store(image) if image is not None and image.filename else None
    try:
        return state.repository.create(user.username, clean_title, clean_content, parsed_tags, name)
    except Exception:
        if name is not None:
            state.media.remove(name)
        raise


@router.get("/api/posts/{post_id}/image")
def post_image(request: Request, post_id: int) -> FileResponse:
    state = context(request)
    post = state.repository.get(post_id, current_user(request).username)
    if post is None or post.image_name is None:
        raise HTTPException(404, "Image not found")
    try:
        path = state.media.path(post.image_name)
        if not path.is_file():
            raise ValueError("missing image")
    except ValueError as error:
        raise HTTPException(404, "Image not found") from error
    return FileResponse(path, media_type="image/png" if path.suffix == ".png" else "image/jpeg")


@router.post("/api/posts/{post_id}/like", response_model=LikeResponse)
def toggle_like(request: Request, post_id: int) -> LikeResponse:
    try:
        liked, count = context(request).repository.toggle_like(
            post_id, current_user(request).username
        )
    except KeyError as error:
        raise HTTPException(404, "Post not found") from error
    return LikeResponse(post_id=post_id, liked=liked, like_count=count)


@router.post("/api/posts/{post_id}/comments", response_model=CommentResponse, status_code=201)
def create_comment(request: Request, post_id: int, payload: CommentRequest) -> CommentResponse:
    state = context(request)
    user = current_user(request)
    text = clean_text(payload.text, "Comment", 100)
    try:
        comment, count = state.repository.comment(
            post_id,
            user.username,
            text,
            increment_count=state.settings.bug_mode != "comment_counter",
        )
    except KeyError as error:
        raise HTTPException(404, "Post not found") from error
    return CommentResponse(post_id=post_id, comment=comment, comment_count=count)


@router.get("/api/unstable", response_model=None)
async def unstable(
    mode: Literal["ok", "delay", "error", "invalid"] = "ok",
) -> JSONResponse | PlainTextResponse:
    if mode == "delay":
        await asyncio.sleep(0.4)
    if mode == "error":
        return JSONResponse({"detail": "Simulated upstream failure"}, status_code=500)
    if mode == "invalid":
        return PlainTextResponse("not-json", media_type="application/json")
    return JSONResponse({"status": "ready", "mode": mode})


@router.post("/api/upload", response_model=UploadResponse)
async def upload(request: Request, file: Annotated[UploadFile, File()]) -> UploadResponse:
    current_user(request)
    content = await file.read(MAX_IMAGE_BYTES + 1)
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "Upload is too large")
    return UploadResponse(filename=Path(file.filename or "unnamed").name, size=len(content))


@router.get("/api/download")
def download(request: Request) -> PlainTextResponse:
    current_user(request)
    return PlainTextResponse(
        "id,name,status\n1,Alpha,Active\n",
        headers={"Content-Disposition": 'attachment; filename="items.csv"'},
        media_type="text/csv",
    )


@router.post("/api/reset", status_code=204)
def reset(request: Request) -> None:
    state = context(request)
    if not state.settings.testing:
        raise HTTPException(404, "Not found")
    if not hmac.compare_digest(
        request.headers.get("X-Practice-Control", ""),
        state.settings.control_token.get_secret_value(),
    ):
        raise HTTPException(403, "Test control authorization required")
    for name in state.repository.reset():
        state.media.remove(name)


app = create_app()
