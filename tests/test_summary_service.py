from __future__ import annotations

from pathlib import Path
import tempfile
from unittest import TestCase

from app.models import SubtitleSource, SummaryType
from app.repositories import Database, SubtitleRepository, SummaryRepository, VideoRepository
from app.services import SummaryService, SummaryServiceError


class SummaryServiceTests(TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        sqlite_path = Path(self.temp_dir.name) / "videos.db"
        self.database = Database(sqlite_path)
        self.database.init_schema()

        self.video_repo = VideoRepository(self.database)
        self.subtitle_repo = SubtitleRepository(self.database)
        self.summary_repo = SummaryRepository(self.database)
        self.service = SummaryService(
            video_repository=self.video_repo,
            subtitle_repository=self.subtitle_repo,
            summary_repository=self.summary_repo,
        )

        self.video_repo.upsert_video(
            {
                "bvid": "BV1X",
                "title": "Python 学习路径",
                "description": "从变量到函数",
                "owner_name": "UP",
                "owner_mid": 1,
                "duration": 100,
                "pubdate": 1700000000,
                "tags": ["python"],
                "view_count": 1,
                "like_count": 1,
            }
        )

    def test_generate_and_store_uses_subtitle_as_source(self) -> None:
        self.subtitle_repo.create_subtitle(
            "BV1X",
            SubtitleSource.BILIBILI,
            "第一段内容\n第二段内容\n第三段内容\n第四段内容\n第五段内容",
        )
        result = self.service.generate_and_store("BV1X", segment_size=2, keypoint_limit=3)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["counts"]["video"], 1)
        self.assertEqual(result["counts"]["segment"], 3)
        self.assertEqual(result["counts"]["keypoint"], 3)

        rows = self.summary_repo.list_by_bvid("BV1X")
        self.assertEqual(len(rows), 7)
        row_types = [row["type"] for row in rows]
        self.assertEqual(row_types.count(SummaryType.VIDEO.value), 1)
        self.assertEqual(row_types.count(SummaryType.SEGMENT.value), 3)
        self.assertEqual(row_types.count(SummaryType.KEYPOINT.value), 3)

    def test_generate_and_store_falls_back_to_video_metadata(self) -> None:
        result = self.service.generate_and_store("BV1X")
        self.assertIn("Python 学习路径", result["video_summary"])
        rows = self.summary_repo.list_by_bvid("BV1X")
        self.assertGreaterEqual(len(rows), 2)

    def test_generate_and_store_overwrites_existing_summaries(self) -> None:
        self.subtitle_repo.create_subtitle(
            "BV1X",
            SubtitleSource.BILIBILI,
            "初始内容一\n初始内容二",
        )
        self.service.generate_and_store("BV1X", segment_size=2, keypoint_limit=1)
        first_count = len(self.summary_repo.list_by_bvid("BV1X"))
        self.assertEqual(first_count, 3)

        self.subtitle_repo.replace_subtitle_for_source(
            "BV1X",
            SubtitleSource.BILIBILI,
            "重算内容一\n重算内容二\n重算内容三\n重算内容四",
        )
        self.service.generate_and_store("BV1X", segment_size=2, keypoint_limit=2)
        second_rows = self.summary_repo.list_by_bvid("BV1X")
        self.assertEqual(len(second_rows), 5)
        self.assertIn("重算内容一", second_rows[0]["content"])

    def test_generate_and_store_raises_for_missing_video(self) -> None:
        with self.assertRaises(SummaryServiceError) as context:
            self.service.generate_and_store("BV404")
        self.assertEqual(context.exception.status_code, 404)
