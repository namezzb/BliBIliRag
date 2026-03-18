from __future__ import annotations

from unittest import IsolatedAsyncioTestCase

from fastapi import HTTPException

from app.api.routes.videos import get_video, import_favorites, list_favorites, list_videos


class _FakeContentService:
    def __init__(self) -> None:
        self.folders = [
            {"id": 1, "title": "默认收藏夹", "media_count": 3, "is_default": True}
        ]
        self.import_result = {"status": "completed", "folders": [1], "scanned": 3, "imported": 2}

    def get_favorites(self):  # noqa: ANN201
        return self.folders

    def import_favorites(self, folder_ids: list[int]):  # noqa: ANN201
        assert folder_ids == [1]
        return self.import_result


class _FakeVideoRepository:
    def __init__(self) -> None:
        self.data = {
            "BV1": {
                "bvid": "BV1",
                "title": "t1",
                "description": "d1",
                "owner_name": "up",
                "owner_mid": 1,
                "duration": 10,
                "pubdate": 2,
                "tags": ["x"],
                "view_count": 9,
                "like_count": 4,
            }
        }

    def list_videos(self, skip: int, limit: int):  # noqa: ANN201
        _ = skip
        _ = limit
        return [self.data["BV1"]], 1

    def get_by_bvid(self, bvid: str):  # noqa: ANN201
        return self.data.get(bvid)


class VideoRouteTests(IsolatedAsyncioTestCase):
    async def test_list_favorites(self) -> None:
        payload = await list_favorites(service=_FakeContentService())
        self.assertEqual(len(payload), 1)
        self.assertTrue(payload[0]["is_default"])

    async def test_import_favorites(self) -> None:
        service = _FakeContentService()
        request = type("Req", (), {"folder_ids": [1]})()
        payload = await import_favorites(request=request, service=service)
        self.assertEqual(payload["imported"], 2)

    async def test_list_videos(self) -> None:
        repo = _FakeVideoRepository()
        payload = await list_videos(skip=0, limit=20, video_repository=repo)
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["videos"][0]["bvid"], "BV1")

    async def test_get_video_not_found(self) -> None:
        repo = _FakeVideoRepository()
        with self.assertRaises(HTTPException) as context:
            await get_video("BV_UNKNOWN", video_repository=repo)
        self.assertEqual(context.exception.status_code, 404)

