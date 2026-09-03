"""SQLite repository scoped to one application instance's data directory."""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path

from practice_app.models import CommentView, PostView


class Repository:
    def __init__(self, data_dir: Path) -> None:
        self.root = data_dir.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "content.sqlite3"
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT NOT NULL,
                    title TEXT NOT NULL, content TEXT NOT NULL, tags TEXT NOT NULL,
                    image_name TEXT, comment_count INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS likes (
                    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
                    username TEXT NOT NULL, PRIMARY KEY (post_id, username)
                );
                CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                    author TEXT NOT NULL, text TEXT NOT NULL
                );
            """)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        with closing(sqlite3.connect(self.path, timeout=5)) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys = ON")
            with db:
                yield db

    def _view(self, db: sqlite3.Connection, row: sqlite3.Row, username: str) -> PostView:
        likes = db.execute("SELECT username FROM likes WHERE post_id=?", (row["id"],)).fetchall()
        comments = db.execute(
            "SELECT id, author, text FROM comments WHERE post_id=? ORDER BY id", (row["id"],)
        ).fetchall()
        return PostView(
            id=row["id"],
            author=row["author"],
            title=row["title"],
            content=row["content"],
            tags=json.loads(row["tags"]),
            image_name=row["image_name"],
            image_url=f"/api/posts/{row['id']}/image" if row["image_name"] else None,
            like_count=len(likes),
            liked=any(like["username"] == username for like in likes),
            comment_count=row["comment_count"],
            comments=[CommentView(**dict(comment)) for comment in comments],
        )

    def posts(self, username: str, query: str = "") -> list[PostView]:
        with self.connection() as db:
            rows = db.execute("SELECT * FROM posts ORDER BY id DESC").fetchall()
            posts = [self._view(db, row, username) for row in rows]
        needle = query.strip().casefold()
        return [
            post
            for post in posts
            if not needle
            or any(needle in value.casefold() for value in [post.title, post.content, *post.tags])
        ]

    def get(self, post_id: int, username: str) -> PostView | None:
        with self.connection() as db:
            row = db.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
            return self._view(db, row, username) if row else None

    def create(
        self, author: str, title: str, content: str, tags: list[str], image_name: str | None
    ) -> PostView:
        with self.connection() as db:
            cursor = db.execute(
                "INSERT INTO posts(author,title,content,tags,image_name) VALUES (?,?,?,?,?)",
                (author, title, content, json.dumps(tags), image_name),
            )
            row = db.execute("SELECT * FROM posts WHERE id=?", (cursor.lastrowid,)).fetchone()
            return self._view(db, row, author)

    def toggle_like(self, post_id: int, username: str) -> tuple[bool, int]:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM posts WHERE id=?", (post_id,)).fetchone() is None:
                raise KeyError(post_id)
            exists = db.execute(
                "SELECT 1 FROM likes WHERE post_id=? AND username=?", (post_id, username)
            ).fetchone()
            if exists:
                db.execute("DELETE FROM likes WHERE post_id=? AND username=?", (post_id, username))
            else:
                db.execute("INSERT INTO likes VALUES (?,?)", (post_id, username))
            count = db.execute("SELECT COUNT(*) FROM likes WHERE post_id=?", (post_id,)).fetchone()[
                0
            ]
            return not bool(exists), int(count)

    def comment(
        self, post_id: int, author: str, text: str, *, increment_count: bool
    ) -> tuple[CommentView, int]:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM posts WHERE id=?", (post_id,)).fetchone() is None:
                raise KeyError(post_id)
            cursor = db.execute(
                "INSERT INTO comments(post_id,author,text) VALUES (?,?,?)", (post_id, author, text)
            )
            if increment_count:
                db.execute("UPDATE posts SET comment_count=comment_count+1 WHERE id=?", (post_id,))
            count = db.execute("SELECT comment_count FROM posts WHERE id=?", (post_id,)).fetchone()[
                0
            ]
            return CommentView(id=int(cursor.lastrowid or 0), author=author, text=text), int(count)

    def reset(self) -> list[str]:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            names = [
                str(row[0])
                for row in db.execute("SELECT image_name FROM posts WHERE image_name IS NOT NULL")
            ]
            db.execute("DELETE FROM posts")
        return names
