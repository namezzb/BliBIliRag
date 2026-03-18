from __future__ import annotations

from pathlib import Path
import tempfile
from unittest import TestCase

from app.core.config import Settings
from app.models import SubtitleSource
from app.repositories import Database, SessionStore, SubtitleRepository
from app.services import BilibiliAuthError
from app.services.subtitle import SubtitleService, clean_subtitle_text


class _FakeSubtitleClient:
    def __init__(self, mapping: dict[tuple[str, str], dict], fail_urls: set[str] | None = None):
        self.mapping = mapping
        self.fail_urls = fail_urls or set()

    def get_json(self, url: str, params=None, headers=None):  # noqa: ANN001, ANN201
        _ = headers
        if url in self.fail_urls:
            raise BilibiliAuthError("forced fail", 502)
        key = (url, str(params))
        if key not in self.mapping:
            raise AssertionError(f"Unexpected request: {key}")
        return self.mapping[key]


class SubtitleServiceTests(TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        base_path = Path(self.temp_dir.name)
        settings = Settings(
            data_dir=base_path,
            sqlite_path=base_path / "videos.db",
            chroma_path=base_path / "chroma",
            bilibili_session_path=base_path / "session.json",
        )
        settings.ensure_directories()
        store = SessionStore(settings.bilibili_session_path)
        store.save({"SESSDATA": "sess", "bili_jct": "csrf", "DedeUserID": "1"})
        database = Database(settings.sqlite_path)
        database.init_schema()
        with database.connection() as conn:
            conn.execute(
                """
                INSERT INTO videos (bvid, title, description)
                VALUES (?, ?, ?)
                """,
                ("BVX1", "title", "desc"),
            )

        self.settings = settings
        self.store = store
        self.subtitle_repo = SubtitleRepository(database)

    def test_clean_subtitle_text(self) -> None:
        raw = "[00:00] 你好\n00:01 你好\n  \n测试\n哈"
        cleaned = clean_subtitle_text(raw)
        self.assertEqual(cleaned, "你好 测试 哈")

    def test_fetch_and_store_subtitle_with_wbi_fallback(self) -> None:
        mapping = {
            (f"{self.settings.bilibili_api_base}/x/web-interface/view", "{'bvid': 'BVX1'}"): {
                "code": 0,
                "data": {"cid": 999, "bvid": "BVX1"},
            },
            (f"{self.settings.bilibili_api_base}/x/player/v2", "{'bvid': 'BVX1', 'cid': 999}"): {
                "code": 0,
                "data": {
                    "subtitle": {
                        "subtitles": [
                            {"lan": "zh-CN", "subtitle_url": "https://example.com/subtitle.json"}
                        ]
                    }
                },
            },
            ("https://example.com/subtitle.json", "None"): {
                "body": [
                    {"content": "第一句"},
                    {"content": "00:01 第二句"},
                ]
            },
        }
        client = _FakeSubtitleClient(
            mapping=mapping,
            fail_urls={f"{self.settings.bilibili_api_base}/x/player/wbi/v2"},
        )
        service = SubtitleService(
            settings=self.settings,
            api_client=client,
            session_store=self.store,
            subtitle_repository=self.subtitle_repo,
        )

        result = service.fetch_and_store_bilibili_subtitle("BVX1")
        self.assertEqual(result["status"], "completed")
        rows = self.subtitle_repo.list_by_bvid("BVX1")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source"], SubtitleSource.BILIBILI.value)
        self.assertIn("第一句", rows[0]["content"])
        self.assertIn("第二句", rows[0]["content"])

    def test_fetch_subtitle_without_cookie(self) -> None:
        empty_store = SessionStore(Path(self.temp_dir.name) / "empty-session.json")
        service = SubtitleService(
            settings=self.settings,
            api_client=_FakeSubtitleClient({}),
            session_store=empty_store,
            subtitle_repository=self.subtitle_repo,
        )
        with self.assertRaises(BilibiliAuthError):
            service.fetch_and_store_bilibili_subtitle("BVX1")
