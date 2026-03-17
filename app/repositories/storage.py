from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import json
import sqlite3
from typing import Any, Iterator

from app.models import SummaryType, SubtitleSource, TaskStatus
from app.repositories.schema import SCHEMA_SQL


class Database:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self.connection() as conn:
            conn.executescript(SCHEMA_SQL)


class VideoRepository:
    def __init__(self, database: Database):
        self.database = database

    def upsert_video(self, payload: dict[str, Any]) -> dict[str, Any]:
        tags = payload.get("tags", [])
        tags_json = json.dumps(tags, ensure_ascii=True)
        with self.database.connection() as conn:
            conn.execute(
                """
                INSERT INTO videos (
                    bvid, title, description, owner_name, owner_mid, duration, pubdate,
                    tags, view_count, like_count
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(bvid) DO UPDATE SET
                    title=excluded.title,
                    description=excluded.description,
                    owner_name=excluded.owner_name,
                    owner_mid=excluded.owner_mid,
                    duration=excluded.duration,
                    pubdate=excluded.pubdate,
                    tags=excluded.tags,
                    view_count=excluded.view_count,
                    like_count=excluded.like_count,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    payload["bvid"],
                    payload["title"],
                    payload.get("description"),
                    payload.get("owner_name"),
                    payload.get("owner_mid"),
                    payload.get("duration"),
                    payload.get("pubdate"),
                    tags_json,
                    payload.get("view_count"),
                    payload.get("like_count"),
                ),
            )
        result = self.get_by_bvid(payload["bvid"])
        if result is None:
            raise RuntimeError("Failed to upsert video")
        return result

    def get_by_bvid(self, bvid: str) -> dict[str, Any] | None:
        with self.database.connection() as conn:
            row = conn.execute("SELECT * FROM videos WHERE bvid = ?", (bvid,)).fetchone()
        return _row_to_dict(row)

    def count_by_bvid(self, bvid: str) -> int:
        with self.database.connection() as conn:
            row = conn.execute(
                "SELECT COUNT(1) AS total FROM videos WHERE bvid = ?",
                (bvid,),
            ).fetchone()
        return int(row["total"]) if row else 0


class SubtitleRepository:
    def __init__(self, database: Database):
        self.database = database

    def create_subtitle(
        self,
        bvid: str,
        source: SubtitleSource,
        content: str,
        language: str = "zh",
    ) -> int:
        with self.database.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO subtitles (bvid, source, content, language)
                VALUES (?, ?, ?, ?)
                """,
                (bvid, source.value, content, language),
            )
            return int(cursor.lastrowid)

    def list_by_bvid(self, bvid: str) -> list[dict[str, Any]]:
        with self.database.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM subtitles WHERE bvid = ? ORDER BY id ASC",
                (bvid,),
            ).fetchall()
        return [_row_to_dict(row) for row in rows]


class SummaryRepository:
    def __init__(self, database: Database):
        self.database = database

    def create_summary(
        self,
        bvid: str,
        summary_type: SummaryType,
        content: str,
        timestamp: str | None = None,
    ) -> int:
        with self.database.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO summaries (bvid, type, content, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (bvid, summary_type.value, content, timestamp),
            )
            return int(cursor.lastrowid)

    def list_by_bvid(self, bvid: str) -> list[dict[str, Any]]:
        with self.database.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM summaries WHERE bvid = ? ORDER BY id ASC",
                (bvid,),
            ).fetchall()
        return [_row_to_dict(row) for row in rows]


class TaskRepository:
    def __init__(self, database: Database):
        self.database = database

    def create_task(
        self,
        bvid: str,
        task_type: str,
        status: TaskStatus = TaskStatus.PENDING,
        error_message: str | None = None,
    ) -> int:
        with self.database.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO tasks (bvid, task_type, status, error_message)
                VALUES (?, ?, ?, ?)
                """,
                (bvid, task_type, status.value, error_message),
            )
            return int(cursor.lastrowid)

    def get_task(self, task_id: int) -> dict[str, Any] | None:
        with self.database.connection() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return _row_to_dict(row)

    def update_status(
        self,
        task_id: int,
        status: TaskStatus,
        error_message: str | None = None,
    ) -> None:
        with self.database.connection() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status.value, error_message, task_id),
            )


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    payload = dict(row)
    if "tags" in payload and payload["tags"]:
        payload["tags"] = json.loads(payload["tags"])
    elif "tags" in payload:
        payload["tags"] = []
    return payload

