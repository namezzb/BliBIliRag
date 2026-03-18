from __future__ import annotations

from typing import Any

from app.models import SummaryType
from app.repositories import SubtitleRepository, SummaryRepository, VideoRepository

SOURCE_PRIORITY = {
    "bilibili": 0,
    "asr_direct": 1,
    "asr_local": 2,
    "fallback": 3,
}


class SummaryServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class SummaryService:
    def __init__(
        self,
        video_repository: VideoRepository,
        subtitle_repository: SubtitleRepository,
        summary_repository: SummaryRepository,
    ):
        self.video_repository = video_repository
        self.subtitle_repository = subtitle_repository
        self.summary_repository = summary_repository

    def generate_and_store(
        self,
        bvid: str,
        segment_size: int = 8,
        keypoint_limit: int = 5,
    ) -> dict[str, Any]:
        video = self.video_repository.get_by_bvid(bvid)
        if video is None:
            raise SummaryServiceError("video_not_found", 404)

        source_text = self._resolve_source_text(bvid, video)
        lines = self._normalize_lines(source_text)
        if not lines:
            raise SummaryServiceError("summary_source_empty", 422)

        video_summary = self._build_video_summary(video, lines)
        segment_summaries = self._build_segment_summaries(lines, segment_size)
        key_points = self._build_key_points(lines, keypoint_limit)

        self.summary_repository.delete_by_bvid(bvid)
        self.summary_repository.create_summary(
            bvid=bvid,
            summary_type=SummaryType.VIDEO,
            content=video_summary,
        )
        for index, segment in enumerate(segment_summaries, start=1):
            self.summary_repository.create_summary(
                bvid=bvid,
                summary_type=SummaryType.SEGMENT,
                content=segment,
                timestamp=f"segment-{index:02d}",
            )
        for index, key_point in enumerate(key_points, start=1):
            self.summary_repository.create_summary(
                bvid=bvid,
                summary_type=SummaryType.KEYPOINT,
                content=key_point,
                timestamp=f"keypoint-{index:02d}",
            )

        return {
            "status": "completed",
            "bvid": bvid,
            "video_summary": video_summary,
            "segment_summaries": segment_summaries,
            "key_points": key_points,
            "counts": {
                "video": 1,
                "segment": len(segment_summaries),
                "keypoint": len(key_points),
            },
        }

    def _resolve_source_text(self, bvid: str, video: dict[str, Any]) -> str:
        subtitles = self.subtitle_repository.list_by_bvid(bvid)
        if subtitles:
            ordered = sorted(
                subtitles,
                key=lambda item: (
                    SOURCE_PRIORITY.get(str(item.get("source") or ""), 99),
                    int(item.get("id") or 0),
                ),
            )
            content = str(ordered[0].get("content") or "").strip()
            if content:
                return content

        return "\n".join(
            [
                str(video.get("title") or ""),
                str(video.get("description") or ""),
            ]
        ).strip()

    @staticmethod
    def _normalize_lines(text: str) -> list[str]:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        output: list[str] = []
        seen: set[str] = set()
        for line in normalized.split("\n"):
            candidate = " ".join(line.strip().split())
            if not candidate:
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            output.append(candidate)
        return output

    @staticmethod
    def _build_video_summary(video: dict[str, Any], lines: list[str]) -> str:
        head = "；".join(lines[:4])
        title = str(video.get("title") or "")
        if title and title not in head:
            return f"{title}：{head}" if head else title
        return head or title

    @staticmethod
    def _build_segment_summaries(lines: list[str], segment_size: int) -> list[str]:
        size = max(1, segment_size)
        output: list[str] = []
        for start in range(0, len(lines), size):
            chunk = lines[start : start + size]
            segment = "；".join(chunk)
            output.append(segment[:240])
        return output

    @staticmethod
    def _build_key_points(lines: list[str], keypoint_limit: int) -> list[str]:
        limit = max(1, keypoint_limit)
        output: list[str] = []
        for line in lines:
            if len(line) < 6:
                continue
            output.append(line[:120])
            if len(output) >= limit:
                break
        if not output:
            output = [line[:120] for line in lines[:limit]]
        return output
