from __future__ import annotations

from typing import Any
import re

from app.core.config import Settings
from app.models import SubtitleSource
from app.repositories import SessionStore, SubtitleRepository
from app.services.bilibili_auth import BilibiliAPIClient, BilibiliAuthError


class SubtitleService:
    def __init__(
        self,
        settings: Settings,
        api_client: BilibiliAPIClient,
        session_store: SessionStore,
        subtitle_repository: SubtitleRepository,
    ):
        self.settings = settings
        self.api_client = api_client
        self.session_store = session_store
        self.subtitle_repository = subtitle_repository

    def fetch_and_store_bilibili_subtitle(self, bvid: str) -> dict[str, Any]:
        headers = self._user_headers()
        view_payload = self.api_client.get_json(
            f"{self.settings.bilibili_api_base}/x/web-interface/view",
            params={"bvid": bvid},
            headers=headers,
        )
        view_data = view_payload.get("data") or {}
        cid = view_data.get("cid")
        if not cid:
            raise BilibiliAuthError("Cannot resolve cid for subtitle fetch", 502)

        player_data = self._get_player_data(bvid=bvid, cid=int(cid), headers=headers)
        subtitle_url, language = self._extract_subtitle_url(player_data)
        if not subtitle_url:
            raise BilibiliAuthError("Subtitle not found for this video", 404)

        subtitle_payload = self.api_client.get_json(subtitle_url, headers=headers)
        raw_text = self._extract_subtitle_text(subtitle_payload)
        cleaned_text = clean_subtitle_text(raw_text)
        if not cleaned_text:
            raise BilibiliAuthError("Subtitle content is empty after cleaning", 422)

        subtitle_id = self.subtitle_repository.replace_subtitle_for_source(
            bvid=bvid,
            source=SubtitleSource.BILIBILI,
            content=cleaned_text,
            language=language or "zh",
        )
        return {
            "status": "completed",
            "subtitle_id": subtitle_id,
            "source": SubtitleSource.BILIBILI.value,
            "language": language or "zh",
            "length": len(cleaned_text),
        }

    def _get_player_data(
        self,
        bvid: str,
        cid: int,
        headers: dict[str, str],
    ) -> dict[str, Any]:
        wbi_url = f"{self.settings.bilibili_api_base}/x/player/wbi/v2"
        fallback_url = f"{self.settings.bilibili_api_base}/x/player/v2"
        params = {"bvid": bvid, "cid": cid}
        try:
            payload = self.api_client.get_json(wbi_url, params=params, headers=headers)
            return payload.get("data") or {}
        except BilibiliAuthError:
            payload = self.api_client.get_json(fallback_url, params=params, headers=headers)
            return payload.get("data") or {}

    @staticmethod
    def _extract_subtitle_url(player_data: dict[str, Any]) -> tuple[str, str | None]:
        subtitle = player_data.get("subtitle") or {}
        entries = subtitle.get("subtitles") or []
        if not entries:
            return "", None

        preferred = None
        for entry in entries:
            lan = str(entry.get("lan") or "")
            if lan.startswith("zh"):
                preferred = entry
                break
        target = preferred or entries[0]
        return (str(target.get("subtitle_url") or ""), target.get("lan"))

    @staticmethod
    def _extract_subtitle_text(payload: dict[str, Any]) -> str:
        body = payload.get("body")
        if isinstance(body, list):
            lines = []
            for item in body:
                if isinstance(item, dict):
                    content = str(item.get("content") or "")
                    if content:
                        lines.append(content)
            return "\n".join(lines)
        if "content" in payload:
            return str(payload.get("content") or "")
        return ""

    def _user_headers(self) -> dict[str, str]:
        cookie_header = self.session_store.build_cookie_header()
        if not cookie_header:
            raise BilibiliAuthError("No bilibili session found, please login first", 401)
        return {
            "User-Agent": self.settings.bilibili_user_agent,
            "Referer": self.settings.bilibili_referer,
            "Origin": self.settings.bilibili_origin,
            "Cookie": cookie_header,
        }


def clean_subtitle_text(text: str) -> str:
    if not text:
        return ""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned_lines: list[str] = []
    seen: set[str] = set()
    for raw_line in normalized.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"\[\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?\]", " ", line)
        line = re.sub(r"\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?", " ", line)
        line = re.sub(r"\s+", " ", line).strip()
        if not line:
            continue
        if line in seen:
            continue
        seen.add(line)
        cleaned_lines.append(line)

    merged: list[str] = []
    for line in cleaned_lines:
        if merged and len(line) <= 4:
            merged[-1] = f"{merged[-1]} {line}".strip()
            continue
        merged.append(line)
    return "\n".join(merged)

