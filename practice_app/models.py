"""Request and response models for the local practice application."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class UserView(BaseModel):
    username: str
    role: str


class Item(BaseModel):
    id: int
    name: str
    category: str
    status: str


class ItemsResponse(BaseModel):
    items: list[Item]
    total: int
    page: int
    page_size: int


class UploadResponse(BaseModel):
    filename: str
    size: int


class CommentRequest(BaseModel):
    text: str


class CommentView(BaseModel):
    id: int
    author: str
    text: str


class PostView(BaseModel):
    id: int
    author: str
    title: str
    content: str
    tags: list[str]
    image_name: str | None = None
    image_url: str | None = None
    like_count: int = 0
    liked: bool = False
    comment_count: int = 0
    comments: list[CommentView] = Field(default_factory=list)


class PostsResponse(BaseModel):
    posts: list[PostView]
    total: int


class LikeResponse(BaseModel):
    post_id: int
    liked: bool
    like_count: int


class CommentResponse(BaseModel):
    post_id: int
    comment: CommentView
    comment_count: int
