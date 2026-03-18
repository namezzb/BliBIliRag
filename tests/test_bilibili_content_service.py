from __future__ import annotations

from pathlib import Path
import tempfile
from unittest import TestCase

from app.core.config import Settings
from app.repositories import Database, SessionStore, VideoRepository
from app.services import BilibiliContentError, BilibiliContentService


class _FakeContentApiClient:
    def __init__(self, mapping: dict[str, dict]):
        self.mapping = mapping
        self.calls: list[str] = []

    def get_json(self, url: str, params=None, headers=None):  # noqa: ANN001, ANN201
        _ = headers
        key = f"{url}|{params}"
        self.calls.append(key)
        if key not in self.mapping:
            raise AssertionError(f"Unexpected request: {key}")
        return self.mapping[key]


class BilibiliContentServiceTests(TestCase):
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
        self.store = SessionStore(self.settings.bilibili_session_path)
        self.store.save({"SESSDATA": "sess", "bili_jct": "csrf", "DedeUserID": "9"})
        self.database = Database(self.settings.sqlite_path)
        self.database.init_schema()
        self.video_repo = VideoRepository(self.database)

    def test_get_favorites_marks_default_folder(self) -> None:
        api = _FakeContentApiClient(
            {
                f"{self.settings.bilibili_api_base}/x/web-interface/nav|None": {
                    "code": 0,
                    "data": {"mid": 1234},
                },
                f"{self.settings.bilibili_api_base}/x/v3/fav/folder/created/list-all|{{'up_mid': 1234}}": {
                    "code": 0,
                    "data": {
                        "list": [
                            {"id": 1, "title": "默认收藏夹", "media_count": 4},
                            {"id": 2, "title": "技术", "media_count": 10, "is_default": 0},
                        ]
                    },
                },
            }
        )
        service = BilibiliContentService(
            settings=self.settings,
            api_client=api,
            session_store=self.store,
            video_repository=self.video_repo,
        )
        folders = service.get_favorites()
        self.assertEqual(len(folders), 2)
        self.assertTrue(folders[0]["is_default"])
        self.assertFalse(folders[1]["is_default"])

    def test_get_favorite_videos_enforces_ps_limit(self) -> None:
        service = BilibiliContentService(
            settings=self.settings,
            api_client=_FakeContentApiClient({}),
            session_store=self.store,
            video_repository=self.video_repo,
        )
        with self.assertRaises(BilibiliContentError):
            service.get_favorite_videos(media_id=1, ps=21)

    def test_get_favorite_videos_filters_invalid_items(self) -> None:
        api = _FakeContentApiClient(
            {
                f"{self.settings.bilibili_api_base}/x/v3/fav/resource/list|{{'media_id': 2, 'pn': 1, 'ps': 20, 'platform': 'web'}}": {
                    "code": 0,
                    "data": {
                        "medias": [
                            {"bvid": "BV_VALID_1", "title": "正常视频", "attr": 0},
                            {"bvid": "BV_INVALID", "title": "已失效视频", "attr": 0},
                            {"bvid": "BV_ATTR_INVALID", "title": "title", "attr": 9},
                        ],
                        "has_more": False,
                    },
                }
            }
        )
        service = BilibiliContentService(
            settings=self.settings,
            api_client=api,
            session_store=self.store,
            video_repository=self.video_repo,
        )
        page = service.get_favorite_videos(media_id=2)
        self.assertEqual(len(page["items"]), 1)
        self.assertEqual(page["items"][0]["bvid"], "BV_VALID_1")

    def test_import_favorites_writes_video_metadata(self) -> None:
        api = _FakeContentApiClient(
            {
                f"{self.settings.bilibili_api_base}/x/web-interface/nav|None": {
                    "code": 0,
                    "data": {"mid": 7},
                },
                f"{self.settings.bilibili_api_base}/x/v3/fav/folder/created/list-all|{{'up_mid': 7}}": {
                    "code": 0,
                    "data": {"list": [{"id": 101, "title": "技术", "media_count": 1}]},
                },
                f"{self.settings.bilibili_api_base}/x/v3/fav/resource/list|{{'media_id': 101, 'pn': 1, 'ps': 20, 'platform': 'web'}}": {
                    "code": 0,
                    "data": {"medias": [{"bvid": "BV1A"}], "has_more": False},
                },
                f"{self.settings.bilibili_api_base}/x/web-interface/view|{{'bvid': 'BV1A'}}": {
                    "code": 0,
                    "data": {
                        "bvid": "BV1A",
                        "title": "Video A",
                        "desc": "Desc A",
                        "owner": {"name": "UP", "mid": 88},
                        "duration": 500,
                        "pubdate": 1700000000,
                        "tags": ["python"],
                        "stat": {"view": 100, "like": 10},
                    },
                },
            }
        )
        service = BilibiliContentService(
            settings=self.settings,
            api_client=api,
            session_store=self.store,
            video_repository=self.video_repo,
        )
        result = service.import_favorites([101])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["imported"], 1)
        video = self.video_repo.get_by_bvid("BV1A")
        assert video is not None
        self.assertEqual(video["title"], "Video A")
        self.assertEqual(video["tags"], ["python"])

