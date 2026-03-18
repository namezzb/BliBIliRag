from __future__ import annotations

from pathlib import Path
import tempfile
from unittest import TestCase

from app.core.config import Settings
from app.models import SummaryType
from app.repositories import Database, SummaryRepository, VideoRepository
from app.services import IndexingService, IndexingServiceError, LocalJsonVectorStore


class IndexingServiceTests(TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        base_path = Path(self.temp_dir.name)
        self.settings = Settings(
            data_dir=base_path,
            sqlite_path=base_path / "videos.db",
            chroma_path=base_path / "chroma",
            bilibili_session_path=base_path / "session.json",
        )
        self.settings.ensure_directories()

        database = Database(self.settings.sqlite_path)
        database.init_schema()
        self.video_repo = VideoRepository(database)
        self.summary_repo = SummaryRepository(database)
        self.vector_store = LocalJsonVectorStore(self.settings.chroma_path / "bilibili_videos.json")
        self.service = IndexingService(
            settings=self.settings,
            video_repository=self.video_repo,
            summary_repository=self.summary_repo,
            vector_store=self.vector_store,
        )

        self.video_repo.upsert_video(
            {
                "bvid": "BV1A",
                "title": "第一条视频",
                "description": "desc",
                "owner_name": "UPA",
                "owner_mid": 1,
                "duration": 10,
                "pubdate": 1,
                "tags": ["python"],
                "view_count": 1,
                "like_count": 1,
            }
        )
        self.video_repo.upsert_video(
            {
                "bvid": "BV1B",
                "title": "第二条视频",
                "description": "desc",
                "owner_name": "UPB",
                "owner_mid": 2,
                "duration": 20,
                "pubdate": 2,
                "tags": ["rag"],
                "view_count": 2,
                "like_count": 2,
            }
        )
        self.summary_repo.create_summary("BV1A", SummaryType.VIDEO, "视频A总览")
        self.summary_repo.create_summary("BV1A", SummaryType.SEGMENT, "视频A分段1", "segment-01")
        self.summary_repo.create_summary("BV1A", SummaryType.KEYPOINT, "视频A要点1", "keypoint-01")
        self.summary_repo.create_summary("BV1B", SummaryType.VIDEO, "视频B总览")

    def test_index_video_upserts_docs_for_single_video(self) -> None:
        result = self.service.index_video("BV1A")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["indexed"], 3)
        self.assertEqual(self.vector_store.count(), 3)

    def test_index_video_is_idempotent_for_same_bvid(self) -> None:
        self.service.index_video("BV1A")
        first_count = self.vector_store.count()
        self.summary_repo.create_summary("BV1A", SummaryType.KEYPOINT, "视频A要点2", "keypoint-02")
        self.service.index_video("BV1A")
        second_count = self.vector_store.count()
        self.assertEqual(first_count + 1, second_count)

    def test_reindex_all_indexes_all_videos_with_summary(self) -> None:
        result = self.service.reindex_all()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["videos"], 2)
        self.assertEqual(result["docs"], 4)
        self.assertEqual(self.vector_store.count(), 4)

    def test_index_video_raises_when_video_missing(self) -> None:
        with self.assertRaises(IndexingServiceError) as context:
            self.service.index_video("BV404")
        self.assertEqual(context.exception.status_code, 404)

    def test_index_video_raises_when_summary_missing(self) -> None:
        self.video_repo.upsert_video(
            {
                "bvid": "BV1C",
                "title": "无摘要视频",
                "description": "desc",
                "owner_name": "UPC",
                "owner_mid": 3,
                "duration": 30,
                "pubdate": 3,
                "tags": ["none"],
                "view_count": 3,
                "like_count": 3,
            }
        )
        with self.assertRaises(IndexingServiceError) as context:
            self.service.index_video("BV1C")
        self.assertEqual(context.exception.status_code, 422)
