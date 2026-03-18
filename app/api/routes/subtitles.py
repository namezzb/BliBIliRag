from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_subtitle_service
from app.services import BilibiliAuthError, SubtitleService

router = APIRouter(prefix="/api/videos", tags=["subtitles"])


class SubtitleFetchResponse(BaseModel):
    status: str
    subtitle_id: int
    source: str
    language: str
    length: int


@router.post("/{bvid}/subtitle/fetch", response_model=SubtitleFetchResponse)
async def fetch_subtitle(
    bvid: str,
    service: SubtitleService = Depends(get_subtitle_service),
) -> dict[str, str | int]:
    try:
        return service.fetch_and_store_bilibili_subtitle(bvid)
    except BilibiliAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

