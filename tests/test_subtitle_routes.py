from __future__ import annotations

from unittest import IsolatedAsyncioTestCase

from fastapi import HTTPException

from app.api.routes.subtitles import fetch_subtitle
from app.services import BilibiliAuthError


class _FakeSubtitleService:
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    def fetch_and_store_bilibili_subtitle(self, bvid: str):  # noqa: ANN201
        if self.should_fail:
            raise BilibiliAuthError("no subtitle", 404)
        return {
            "status": "completed",
            "subtitle_id": 1,
            "source": "bilibili",
            "language": "zh-CN",
            "length": 20,
            "bvid": bvid,
        }


class SubtitleRouteTests(IsolatedAsyncioTestCase):
    async def test_fetch_subtitle_success(self) -> None:
        payload = await fetch_subtitle("BVTEST", service=_FakeSubtitleService())
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["subtitle_id"], 1)

    async def test_fetch_subtitle_error(self) -> None:
        with self.assertRaises(HTTPException) as context:
            await fetch_subtitle("BVTEST", service=_FakeSubtitleService(should_fail=True))
        self.assertEqual(context.exception.status_code, 404)

