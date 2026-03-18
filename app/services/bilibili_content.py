from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.repositories import SessionStore, VideoRepository
from app.services.bilibili_auth import BilibiliAPIClient, BilibiliAuthError


class BilibiliContentError(BilibiliAuthError):
    """Content-related Bilibili errors."""


class BilibiliContentService:
    def __init__(
        self,
        settings: Settings,
        api_client: BilibiliAPIClient,
        session_store: SessionStore,
        video_repository: VideoRepository,
    ):
        self.settings = settings
        self.api_client = api_client
        self.session_store = session_store
        self.video_repository = video_repository

    def get_favorites(self) -> list[dict[str, Any]]:
        headers = self._user_headers()
        nav_payload = self.api_client.get_json(
            f"{self.settings.bilibili_api_base}/x/web-interface/nav",
            headers=headers,
        )
        mid = (nav_payload.get("data") or {}).get("mid")
        if not mid:
            raise BilibiliContentError("Cannot resolve user mid from session", 502)

        payload = self.api_client.get_json(
            f"{self.settings.bilibili_api_base}/x/v3/fav/folder/created/list-all",
            params={"up_mid": int(mid)},
            headers=headers,
        )
        folders = (payload.get("data") or {}).get("list") or []
        normalized: list[dict[str, Any]] = []
        for folder in folders:
            folder_id = folder.get("id") or folder.get("media_id")
            if not folder_id:
                continue
            normalized.append(
                {
                    "id": int(folder_id),
                    "title": str(folder.get("title") or ""),
                    "media_count": int(folder.get("media_count") or 0),
                    "is_default": self._is_default_folder(folder),
                }
            )
        return normalized

    def get_favorite_videos(
        self,
        media_id: int,
        pn: int = 1,
        ps: int = 20,
    ) -> dict[str, Any]:
        if ps > 20:
            raise BilibiliContentError("Bilibili API requires ps <= 20", 422)
        if pn <= 0:
            raise BilibiliContentError("pn must be >= 1", 422)
        headers = self._user_headers()
        payload = self.api_client.get_json(
            f"{self.settings.bilibili_api_base}/x/v3/fav/resource/list",
            params={
                "media_id": int(media_id),
                "pn": int(pn),
                "ps": int(ps),
                "platform": "web",
            },
            headers=headers,
        )
        data = payload.get("data") or {}
        medias = data.get("medias") or []
        valid_items = [
            item for item in medias if not self._is_invalid_video(item) and item.get("bvid")
        ]
        has_more = bool(data.get("has_more") or data.get("hasMore"))
        return {"items": valid_items, "has_more": has_more}

    def get_video_info(self, bvid: str) -> dict[str, Any]:
        headers = self._user_headers()
        payload = self.api_client.get_json(
            f"{self.settings.bilibili_api_base}/x/web-interface/view",
            params={"bvid": bvid},
            headers=headers,
        )
        data = payload.get("data") or {}
        if not data:
            raise BilibiliContentError("Video info is empty", 502)
        return {
            "bvid": str(data.get("bvid") or bvid),
            "title": str(data.get("title") or ""),
            "description": str(data.get("desc") or ""),
            "owner_name": str((data.get("owner") or {}).get("name") or ""),
            "owner_mid": int((data.get("owner") or {}).get("mid") or 0),
            "duration": int(data.get("duration") or 0),
            "pubdate": int(data.get("pubdate") or 0),
            "tags": [str(tag) for tag in data.get("tags") or []],
            "view_count": int((data.get("stat") or {}).get("view") or 0),
            "like_count": int((data.get("stat") or {}).get("like") or 0),
        }

    def import_favorites(self, folder_ids: list[int]) -> dict[str, Any]:
        target_folders = set(folder_ids)
        if not target_folders:
            raise BilibiliContentError("folder_ids cannot be empty", 422)

        folders = self.get_favorites()
        selected = [folder for folder in folders if folder["id"] in target_folders]
        if not selected:
            raise BilibiliContentError("No matching favorite folders found", 404)

        imported = 0
        scanned = 0
        for folder in selected:
            pn = 1
            while True:
                page = self.get_favorite_videos(folder["id"], pn=pn, ps=20)
                items = page["items"]
                scanned += len(items)
                for item in items:
                    bvid = str(item.get("bvid") or "")
                    if not bvid:
                        continue
                    video_payload = self.get_video_info(bvid)
                    self.video_repository.upsert_video(video_payload)
                    imported += 1
                if not page["has_more"]:
                    break
                pn += 1

        return {
            "status": "completed",
            "folders": [folder["id"] for folder in selected],
            "scanned": scanned,
            "imported": imported,
        }

    def _user_headers(self) -> dict[str, str]:
        cookie_header = self.session_store.build_cookie_header()
        if not cookie_header:
            raise BilibiliContentError("No bilibili session found, please login first", 401)
        return {
            "User-Agent": self.settings.bilibili_user_agent,
            "Referer": self.settings.bilibili_referer,
            "Origin": self.settings.bilibili_origin,
            "Cookie": cookie_header,
        }

    @staticmethod
    def _is_default_folder(folder: dict[str, Any]) -> bool:
        for key in ("is_default", "default", "isDefault"):
            value = folder.get(key)
            if value in (1, True, "1", "true", "True"):
                return True
        for key in ("type", "fav_state"):
            value = folder.get(key)
            if value in (1, "1"):
                return True
        attr_value = folder.get("attr")
        if isinstance(attr_value, int) and attr_value & 1 == 1:
            return True
        title = str(folder.get("title") or "")
        return title in {"默认收藏夹", "默认", "Default Favorites"}

    @staticmethod
    def _is_invalid_video(item: dict[str, Any]) -> bool:
        attr = item.get("attr")
        title = str(item.get("title") or "")
        return attr == 9 or title in {"已失效视频", "已删除视频"}

