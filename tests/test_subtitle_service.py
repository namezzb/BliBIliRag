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


class _FakeASREngine:
    def __init__(
        self,
        direct_text: str | None = None,
        local_text: str | None = None,
        direct_error: BilibiliAuthError | None = None,
        local_error: BilibiliAuthError | None = None,
    ):
        self.direct_text = direct_text
        self.local_text = local_text
        self.direct_error = direct_error
        self.local_error = local_error
        self.local_calls = 0

    def transcribe_from_url(self, audio_url: str, headers: dict[str, str]) -> str:
        _ = (audio_url, headers)
        if self.direct_error is not None:
            raise self.direct_error
        return self.direct_text or ""

    def transcribe_from_file(self, file_path: str) -> str:
        _ = file_path
        self.local_calls += 1
        if self.local_error is not None:
            raise self.local_error
        return self.local_text or ""


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

    def test_fetch_and_store_subtitle_uses_asr_direct_fallback(self) -> None:
        mapping = {
            (f"{self.settings.bilibili_api_base}/x/web-interface/view", "{'bvid': 'BVX1'}"): {
                "code": 0,
                "data": {"cid": 999, "bvid": "BVX1", "title": "标题", "desc": "描述"},
            },
            (f"{self.settings.bilibili_api_base}/x/player/v2", "{'bvid': 'BVX1', 'cid': 999}"): {
                "code": 0,
                "data": {"subtitle": {"subtitles": []}},
            },
            (
                f"{self.settings.bilibili_api_base}/x/player/playurl",
                "{'bvid': 'BVX1', 'cid': 999, 'fnval': 16, 'qn': 80}",
            ): {
                "code": 0,
                "data": {"dash": {"audio": [{"baseUrl": "https://example.com/audio.m4s"}]}},
            },
        }
        client = _FakeSubtitleClient(
            mapping=mapping,
            fail_urls={
                f"{self.settings.bilibili_api_base}/x/player/wbi/v2",
                f"{self.settings.bilibili_api_base}/x/player/wbi/playurl",
            },
        )
        asr_engine = _FakeASREngine(direct_text="00:01 直链转写内容")
        service = SubtitleService(
            settings=self.settings,
            api_client=client,
            session_store=self.store,
            subtitle_repository=self.subtitle_repo,
            asr_engine=asr_engine,
        )

        result = service.fetch_and_store_bilibili_subtitle("BVX1")
        self.assertEqual(result["source"], SubtitleSource.ASR_DIRECT.value)
        rows = self.subtitle_repo.list_by_bvid("BVX1")
        self.assertEqual(rows[0]["source"], SubtitleSource.ASR_DIRECT.value)
        self.assertIn("直链转写内容", rows[0]["content"])

    def test_fetch_and_store_subtitle_uses_local_asr_when_direct_fails(self) -> None:
        mapping = {
            (f"{self.settings.bilibili_api_base}/x/web-interface/view", "{'bvid': 'BVX1'}"): {
                "code": 0,
                "data": {"cid": 999, "bvid": "BVX1", "title": "标题", "desc": "描述"},
            },
            (f"{self.settings.bilibili_api_base}/x/player/v2", "{'bvid': 'BVX1', 'cid': 999}"): {
                "code": 0,
                "data": {"subtitle": {"subtitles": []}},
            },
            (
                f"{self.settings.bilibili_api_base}/x/player/playurl",
                "{'bvid': 'BVX1', 'cid': 999, 'fnval': 16, 'qn': 80}",
            ): {
                "code": 0,
                "data": {"dash": {"audio": [{"baseUrl": "https://example.com/audio.m4s"}]}},
            },
        }
        client = _FakeSubtitleClient(
            mapping=mapping,
            fail_urls={
                f"{self.settings.bilibili_api_base}/x/player/wbi/v2",
                f"{self.settings.bilibili_api_base}/x/player/wbi/playurl",
            },
        )
        asr_engine = _FakeASREngine(
            direct_error=BilibiliAuthError("direct failed", 502),
            local_text="00:01 本地转写内容",
        )

        local_audio = Path(self.temp_dir.name) / "sample.audio"
        local_audio.write_bytes(b"audio-bytes")

        service = SubtitleService(
            settings=self.settings,
            api_client=client,
            session_store=self.store,
            subtitle_repository=self.subtitle_repo,
            asr_engine=asr_engine,
            audio_downloader=lambda _audio_url, _headers: local_audio,
        )

        result = service.fetch_and_store_bilibili_subtitle("BVX1")
        self.assertEqual(result["source"], SubtitleSource.ASR_LOCAL.value)
        self.assertFalse(local_audio.exists())
        rows = self.subtitle_repo.list_by_bvid("BVX1")
        self.assertEqual(rows[0]["source"], SubtitleSource.ASR_LOCAL.value)
        self.assertIn("本地转写内容", rows[0]["content"])
        self.assertEqual(asr_engine.local_calls, 1)

    def test_fetch_and_store_subtitle_falls_back_to_title_desc(self) -> None:
        mapping = {
            (f"{self.settings.bilibili_api_base}/x/web-interface/view", "{'bvid': 'BVX1'}"): {
                "code": 0,
                "data": {
                    "cid": 999,
                    "bvid": "BVX1",
                    "title": "Python 入门教程",
                    "desc": "讲解变量与函数",
                },
            },
            (f"{self.settings.bilibili_api_base}/x/player/v2", "{'bvid': 'BVX1', 'cid': 999}"): {
                "code": 0,
                "data": {"subtitle": {"subtitles": []}},
            },
            (
                f"{self.settings.bilibili_api_base}/x/player/playurl",
                "{'bvid': 'BVX1', 'cid': 999, 'fnval': 16, 'qn': 80}",
            ): {
                "code": 0,
                "data": {"dash": {"audio": [{"baseUrl": "https://example.com/audio.m4s"}]}},
            },
        }
        client = _FakeSubtitleClient(
            mapping=mapping,
            fail_urls={
                f"{self.settings.bilibili_api_base}/x/player/wbi/v2",
                f"{self.settings.bilibili_api_base}/x/player/wbi/playurl",
            },
        )
        asr_engine = _FakeASREngine(
            direct_error=BilibiliAuthError("direct failed", 502),
            local_error=BilibiliAuthError("local failed", 502),
        )

        local_audio = Path(self.temp_dir.name) / "sample2.audio"
        local_audio.write_bytes(b"audio-bytes")

        service = SubtitleService(
            settings=self.settings,
            api_client=client,
            session_store=self.store,
            subtitle_repository=self.subtitle_repo,
            asr_engine=asr_engine,
            audio_downloader=lambda _audio_url, _headers: local_audio,
        )

        result = service.fetch_and_store_bilibili_subtitle("BVX1")
        self.assertEqual(result["source"], SubtitleSource.FALLBACK.value)
        rows = self.subtitle_repo.list_by_bvid("BVX1")
        self.assertEqual(rows[0]["source"], SubtitleSource.FALLBACK.value)
        self.assertIn("Python 入门教程", rows[0]["content"])
        self.assertIn("讲解变量与函数", rows[0]["content"])
