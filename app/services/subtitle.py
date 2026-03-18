from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Protocol
from urllib.request import Request, urlopen
import re
import tempfile

from app.core.config import Settings
from app.models import SubtitleSource
from app.repositories import SessionStore, SubtitleRepository
from app.services.bilibili_auth import BilibiliAPIClient, BilibiliAuthError


class ASREngine(Protocol):
    def transcribe_from_url(self, audio_url: str, headers: dict[str, str]) -> str: ...

    def transcribe_from_file(self, file_path: str) -> str: ...


class NullASREngine:
    def transcribe_from_url(self, audio_url: str, headers: dict[str, str]) -> str:
        _ = (audio_url, headers)
        raise BilibiliAuthError("ASR engine is not configured", 503)

    def transcribe_from_file(self, file_path: str) -> str:
        _ = file_path
        raise BilibiliAuthError("ASR engine is not configured", 503)


class SubtitleService:
    def __init__(
        self,
        settings: Settings,
        api_client: BilibiliAPIClient,
        session_store: SessionStore,
        subtitle_repository: SubtitleRepository,
        asr_engine: ASREngine | None = None,
        audio_downloader: Callable[[str, dict[str, str]], Path] | None = None,
    ):
        self.settings = settings
        self.api_client = api_client
        self.session_store = session_store
        self.subtitle_repository = subtitle_repository
        self.asr_engine = asr_engine or NullASREngine()
        self.audio_downloader = audio_downloader or self._download_audio_to_tempfile

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
        if subtitle_url:
            subtitle_payload = self.api_client.get_json(subtitle_url, headers=headers)
            raw_text = self._extract_subtitle_text(subtitle_payload)
            cleaned_text = clean_subtitle_text(raw_text)
            if cleaned_text:
                return self._persist_result(
                    bvid=bvid,
                    source=SubtitleSource.BILIBILI,
                    content=cleaned_text,
                    language=language or "zh",
                )

        audio_url = self._get_audio_url(bvid=bvid, cid=int(cid), headers=headers)
        if audio_url:
            try:
                direct_text = self.asr_engine.transcribe_from_url(audio_url, headers)
                cleaned_direct = clean_subtitle_text(direct_text)
                if cleaned_direct:
                    return self._persist_result(
                        bvid=bvid,
                        source=SubtitleSource.ASR_DIRECT,
                        content=cleaned_direct,
                        language="zh",
                    )
            except BilibiliAuthError:
                pass

            local_file: Path | None = None
            try:
                local_file = self.audio_downloader(audio_url, headers)
                local_text = self.asr_engine.transcribe_from_file(str(local_file))
                cleaned_local = clean_subtitle_text(local_text)
                if cleaned_local:
                    return self._persist_result(
                        bvid=bvid,
                        source=SubtitleSource.ASR_LOCAL,
                        content=cleaned_local,
                        language="zh",
                    )
            except BilibiliAuthError:
                pass
            finally:
                if local_file and local_file.exists():
                    local_file.unlink(missing_ok=True)

        fallback_text = clean_subtitle_text(
            "\n".join(
                [
                    str(view_data.get("title") or ""),
                    str(view_data.get("desc") or ""),
                ]
            )
        )
        if fallback_text:
            return self._persist_result(
                bvid=bvid,
                source=SubtitleSource.FALLBACK,
                content=fallback_text,
                language="zh",
            )

        raise BilibiliAuthError("Subtitle and ASR are unavailable for this video", 422)

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

    def _get_audio_url(self, bvid: str, cid: int, headers: dict[str, str]) -> str:
        wbi_url = f"{self.settings.bilibili_api_base}/x/player/wbi/playurl"
        fallback_url = f"{self.settings.bilibili_api_base}/x/player/playurl"
        params = {"bvid": bvid, "cid": cid, "fnval": 16, "qn": 80}
        try:
            payload = self.api_client.get_json(wbi_url, params=params, headers=headers)
            data = payload.get("data") or {}
            audio_url = self._extract_audio_url(data)
            if audio_url:
                return audio_url
        except BilibiliAuthError:
            pass

        payload = self.api_client.get_json(fallback_url, params=params, headers=headers)
        return self._extract_audio_url(payload.get("data") or {})

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

    @staticmethod
    def _extract_audio_url(playurl_data: dict[str, Any]) -> str:
        dash = playurl_data.get("dash") or {}
        audios = dash.get("audio") or []
        for audio in audios:
            if not isinstance(audio, dict):
                continue
            base_url = str(audio.get("baseUrl") or audio.get("base_url") or "")
            if base_url:
                return base_url
        durl = playurl_data.get("durl") or []
        for item in durl:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "")
            if url:
                return url
        return ""

    def _persist_result(
        self,
        bvid: str,
        source: SubtitleSource,
        content: str,
        language: str,
    ) -> dict[str, Any]:
        subtitle_id = self.subtitle_repository.replace_subtitle_for_source(
            bvid=bvid,
            source=source,
            content=content,
            language=language,
        )
        return {
            "status": "completed",
            "subtitle_id": subtitle_id,
            "source": source.value,
            "language": language,
            "length": len(content),
        }

    @staticmethod
    def _download_audio_to_tempfile(audio_url: str, headers: dict[str, str]) -> Path:
        request = Request(audio_url, headers=headers, method="GET")
        with urlopen(request, timeout=15) as response:
            payload = response.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".audio") as temp_file:
            temp_file.write(payload)
            return Path(temp_file.name)

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
