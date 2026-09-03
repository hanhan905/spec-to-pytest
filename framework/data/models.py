"""Framework-facing immutable test data models."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Credentials:
    username: str
    password: str
    role: str


@dataclass(frozen=True, slots=True)
class ItemView:
    item_id: int
    name: str
    category: str
    status: str


@dataclass(frozen=True, slots=True)
class CommunityPostData:
    title: str
    content: str
    tags: str
    comment: str
