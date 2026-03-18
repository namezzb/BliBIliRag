from __future__ import annotations

from pathlib import Path
import tempfile
from unittest import TestCase

from app.repositories.session_store import SessionStore


class SessionStoreTests(TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.store = SessionStore(Path(self.temp_dir.name) / "session.json")

    def test_save_and_load_cookie_payload(self) -> None:
        self.store.save(
            {
                "SESSDATA": "sess",
                "bili_jct": "csrf",
                "DedeUserID": "12345",
            }
        )
        loaded = self.store.load()
        self.assertEqual(loaded["SESSDATA"], "sess")
        self.assertEqual(loaded["bili_jct"], "csrf")
        self.assertEqual(loaded["DedeUserID"], "12345")

    def test_build_cookie_header_uses_expected_order(self) -> None:
        self.store.save(
            {
                "bili_jct": "csrf",
                "DedeUserID": "1",
                "SESSDATA": "sess",
            }
        )
        header = self.store.build_cookie_header()
        self.assertEqual(header, "SESSDATA=sess; bili_jct=csrf; DedeUserID=1")

