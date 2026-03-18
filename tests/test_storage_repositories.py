from __future__ import annotations

from pathlib import Path
import sqlite3
import tempfile
from unittest import TestCase

from app.models import SummaryType, SubtitleSource, TaskStatus
from app.repositories import (
    Database,
    SummaryRepository,
    SubtitleRepository,
    TaskRepository,
    VideoRepository,
)


class StorageRepositoryTests(TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.sqlite_path = Path(self.temp_dir.name) / "videos.db"
        self.database = Database(self.sqlite_path)
        self.database.init_schema()

        self.videos = VideoRepository(self.database)
        self.subtitles = SubtitleRepository(self.database)
        self.summaries = SummaryRepository(self.database)
        self.tasks = TaskRepository(self.database)

    def _insert_sample_video(self, bvid: str = "BV1xx411c7XZ") -> None:
        self.videos.upsert_video(
            {
                "bvid": bvid,
                "title": "first title",
                "description": "desc",
                "owner_name": "up",
                "owner_mid": 1001,
                "duration": 120,
                "pubdate": 1700000000,
                "tags": ["python", "rag"],
                "view_count": 10,
                "like_count": 1,
            }
        )

    def test_schema_contains_expected_tables(self) -> None:
        with sqlite3.connect(self.sqlite_path) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        names = {row[0] for row in rows}
        self.assertIn("videos", names)
        self.assertIn("subtitles", names)
        self.assertIn("summaries", names)
        self.assertIn("tasks", names)

    def test_video_upsert_keeps_single_row_per_bvid(self) -> None:
        self._insert_sample_video()
        self.videos.upsert_video(
            {
                "bvid": "BV1xx411c7XZ",
                "title": "updated title",
                "description": "new desc",
                "owner_name": "up2",
                "owner_mid": 2002,
                "duration": 200,
                "pubdate": 1700001111,
                "tags": ["updated"],
                "view_count": 88,
                "like_count": 9,
            }
        )
        self.assertEqual(self.videos.count_by_bvid("BV1xx411c7XZ"), 1)
        stored = self.videos.get_by_bvid("BV1xx411c7XZ")
        assert stored is not None
        self.assertEqual(stored["title"], "updated title")
        self.assertEqual(stored["tags"], ["updated"])

    def test_list_videos_returns_total_and_slice(self) -> None:
        self._insert_sample_video("BV_A")
        self._insert_sample_video("BV_B")
        videos, total = self.videos.list_videos(skip=0, limit=1)
        self.assertEqual(total, 2)
        self.assertEqual(len(videos), 1)

    def test_task_status_transitions(self) -> None:
        self._insert_sample_video()
        task_id = self.tasks.create_task("BV1xx411c7XZ", "fetch")
        created = self.tasks.get_task(task_id)
        assert created is not None
        self.assertEqual(created["status"], TaskStatus.PENDING.value)

        self.tasks.update_status(task_id, TaskStatus.PROCESSING)
        processing = self.tasks.get_task(task_id)
        assert processing is not None
        self.assertEqual(processing["status"], TaskStatus.PROCESSING.value)

        self.tasks.update_status(task_id, TaskStatus.FAILED, error_message="network")
        failed = self.tasks.get_task(task_id)
        assert failed is not None
        self.assertEqual(failed["status"], TaskStatus.FAILED.value)
        self.assertEqual(failed["error_message"], "network")

    def test_subtitle_and_summary_association(self) -> None:
        self._insert_sample_video()
        subtitle_id = self.subtitles.create_subtitle(
            "BV1xx411c7XZ", SubtitleSource.BILIBILI, "subtitle content"
        )
        summary_id = self.summaries.create_summary(
            "BV1xx411c7XZ", SummaryType.SEGMENT, "summary content", "00:00-05:00"
        )

        subtitle_rows = self.subtitles.list_by_bvid("BV1xx411c7XZ")
        summary_rows = self.summaries.list_by_bvid("BV1xx411c7XZ")

        self.assertEqual(subtitle_rows[0]["id"], subtitle_id)
        self.assertEqual(subtitle_rows[0]["source"], SubtitleSource.BILIBILI.value)
        self.assertEqual(summary_rows[0]["id"], summary_id)
        self.assertEqual(summary_rows[0]["type"], SummaryType.SEGMENT.value)

    def test_subtitle_requires_existing_video(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.subtitles.create_subtitle(
                "BV_MISSING", SubtitleSource.ASR_DIRECT, "content"
            )
