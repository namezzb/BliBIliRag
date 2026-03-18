from __future__ import annotations

from pathlib import Path
import json
import tempfile
from typing import Any
from unittest import TestCase

from app.core.config import Settings
from app.repositories import SessionStore
from app.services import BilibiliAPIClient, BilibiliAuthError, BilibiliAuthService


class FakeResponse:
    def __init__(self, payload: dict[str, Any]):
        self._raw = json.dumps(payload, ensure_ascii=True).encode("utf-8")

    def read(self) -> bytes:
        return self._raw

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        return False


class BilibiliAuthServiceTests(TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.session_path = Path(self.temp_dir.name) / "bilibili_session.json"
        self.settings = Settings(
            data_dir=Path(self.temp_dir.name),
            sqlite_path=Path(self.temp_dir.name) / "videos.db",
            chroma_path=Path(self.temp_dir.name) / "chroma",
            bilibili_session_path=self.session_path,
        )
        self.session_store = SessionStore(self.session_path)

    def test_generate_qrcode(self) -> None:
        captured_urls: list[str] = []

        def fake_open(request, timeout: int = 10):  # noqa: ANN001
            captured_urls.append(request.full_url)
            return FakeResponse(
                {
                    "code": 0,
                    "data": {
                        "qrcode_key": "abc-key",
                        "url": "https://example.com/qrcode",
                    },
                }
            )

        service = BilibiliAuthService(
            settings=self.settings,
            api_client=BilibiliAPIClient(open_url=fake_open),
            session_store=self.session_store,
        )
        result = service.generate_qrcode()
        self.assertEqual(result["qrcode_key"], "abc-key")
        self.assertEqual(result["qrcode_url"], "https://example.com/qrcode")
        self.assertTrue(captured_urls[0].endswith("/x/passport-login/web/qrcode/generate"))

    def test_poll_qrcode_status_persists_session(self) -> None:
        callback = (
            "https://passport.bilibili.com/login/success"
            "?SESSDATA=sess123&bili_jct=csrf999&DedeUserID=101"
        )

        def fake_open(request, timeout: int = 10):  # noqa: ANN001
            _ = timeout
            self.assertIn("qrcode_key=key-001", request.full_url)
            return FakeResponse(
                {
                    "code": 0,
                    "data": {"code": 0, "message": "success", "url": callback},
                }
            )

        service = BilibiliAuthService(
            settings=self.settings,
            api_client=BilibiliAPIClient(open_url=fake_open),
            session_store=self.session_store,
        )
        result = service.poll_qrcode_status("key-001")
        self.assertTrue(result["has_session"])
        self.assertEqual(self.session_store.load()["SESSDATA"], "sess123")

    def test_get_user_info_requires_session(self) -> None:
        service = BilibiliAuthService(
            settings=self.settings,
            api_client=BilibiliAPIClient(open_url=lambda *_args, **_kwargs: None),
            session_store=self.session_store,
        )
        with self.assertRaises(BilibiliAuthError):
            service.get_user_info()

    def test_get_user_info_sends_cookie(self) -> None:
        self.session_store.save(
            {"SESSDATA": "sess", "bili_jct": "csrf", "DedeUserID": "66"}
        )
        seen_cookie_headers: list[str] = []

        def fake_open(request, timeout: int = 10):  # noqa: ANN001
            _ = timeout
            header_map = {key.lower(): value for key, value in request.header_items()}
            seen_cookie_headers.append(header_map.get("cookie", ""))
            return FakeResponse(
                {"code": 0, "data": {"isLogin": True, "mid": 66, "uname": "tester"}}
            )

        service = BilibiliAuthService(
            settings=self.settings,
            api_client=BilibiliAPIClient(open_url=fake_open),
            session_store=self.session_store,
        )
        user_info = service.get_user_info()
        self.assertTrue(user_info["is_logged_in"])
        self.assertEqual(user_info["mid"], 66)
        self.assertEqual(user_info["uname"], "tester")
        self.assertIn("SESSDATA=sess", seen_cookie_headers[0])

