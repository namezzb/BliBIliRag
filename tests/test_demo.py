"""
Demo test for BiliBiliRag project.

This is a simple demo test to verify the project setup and basic functionality.
"""
from __future__ import annotations

from pathlib import Path
import tempfile
from unittest import TestCase

from app.repositories import Database, VideoRepository


class DemoTest(TestCase):
    """Demo test case for verifying project setup."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.sqlite_path = Path(self.temp_dir.name) / "test.db"
        self.database = Database(self.sqlite_path)
        self.database.init_schema()
        self.videos = VideoRepository(self.database)

    def test_database_initialization(self) -> None:
        """Test that database schema is initialized correctly."""
        # Should have videos table
        result = self.videos.get_by_bvid("BV_TEST")
        self.assertIsNone(result)  # No videos yet

    def test_video_upsert_and_retrieve(self) -> None:
        """Test basic video insert and retrieve operations."""
        test_video = {
            "bvid": "BV1DemoTest",
            "title": "Demo Test Video",
            "description": "This is a demo test video",
            "owner_name": "DemoUP",
            "owner_mid": 12345,
            "duration": 300,
            "pubdate": 1700000000,
            "tags": ["demo", "test"],
            "view_count": 1000,
            "like_count": 100,
        }

        # Insert video
        result = self.videos.upsert_video(test_video)
        self.assertEqual(result["bvid"], "BV1DemoTest")
        self.assertEqual(result["title"], "Demo Test Video")

        # Retrieve video
        retrieved = self.videos.get_by_bvid("BV1DemoTest")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["title"], "Demo Test Video")
        self.assertEqual(retrieved["tags"], ["demo", "test"])

    def test_video_update(self) -> None:
        """Test that updating a video works correctly."""
        # Insert initial video
        self.videos.upsert_video({
            "bvid": "BV1UpdateTest",
            "title": "Original Title",
            "description": "Original description",
            "owner_name": "UP1",
            "owner_mid": 100,
            "duration": 60,
            "pubdate": 1700000000,
            "tags": ["old"],
            "view_count": 10,
            "like_count": 1,
        })

        # Update video
        self.videos.upsert_video({
            "bvid": "BV1UpdateTest",
            "title": "Updated Title",
            "description": "Updated description",
            "owner_name": "UP2",
            "owner_mid": 200,
            "duration": 120,
            "pubdate": 1700000001,
            "tags": ["new", "updated"],
            "view_count": 999,
            "like_count": 88,
        })

        # Verify update
        result = self.videos.get_by_bvid("BV1UpdateTest")
        assert result is not None
        self.assertEqual(result["title"], "Updated Title")
        self.assertEqual(result["view_count"], 999)
        self.assertEqual(result["tags"], ["new", "updated"])

    def test_list_videos(self) -> None:
        """Test listing videos with pagination."""
        # Insert multiple videos
        for i in range(5):
            self.videos.upsert_video({
                "bvid": f"BV_Test_{i}",
                "title": f"Test Video {i}",
                "description": f"Description {i}",
                "owner_name": "UP",
                "owner_mid": 100,
                "duration": 60,
                "pubdate": 1700000000,
                "tags": ["test"],
                "view_count": 100,
                "like_count": 10,
            })

        # Test list with pagination
        videos, total = self.videos.list_videos(skip=0, limit=3)
        self.assertEqual(total, 5)
        self.assertEqual(len(videos), 3)

        # Test offset
        videos, total = self.videos.list_videos(skip=3, limit=10)
        self.assertEqual(len(videos), 2)