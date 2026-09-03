"""Synthetic demo accounts and read-only dashboard seed data."""

from typing import Final

from practice_app.models import Item

USERS: Final = {
    "admin": {"password": "admin123", "role": "admin"},
    "viewer": {"password": "viewer123", "role": "viewer"},
}

ITEMS: Final = [
    Item(id=1, name="Alpha", category="Desktop", status="Active"),
    Item(id=2, name="Beta", category="Web", status="Paused"),
    Item(id=3, name="Gamma", category="Mobile", status="Active"),
    Item(id=4, name="Delta", category="Web", status="Active"),
    Item(id=5, name="Epsilon", category="Desktop", status="Archived"),
    Item(id=6, name="Zeta", category="Mobile", status="Active"),
]
