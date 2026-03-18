from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_bilibili_content_service, get_video_repository
from app.repositories import VideoRepository
from app.services import BilibiliContentError, BilibiliContentService

router = APIRouter(prefix="/api", tags=["videos"])


class FavoriteFolder(BaseModel):
    id: int
    title: str
    media_count: int
    is_default: bool


class ImportFavoritesRequest(BaseModel):
    folder_ids: list[int] = Field(..., min_length=1)


class ImportFavoritesResponse(BaseModel):
    status: str
    folders: list[int]
    scanned: int
    imported: int


class VideoItem(BaseModel):
    bvid: str
    title: str
    description: str | None
    owner_name: str | None
    owner_mid: int | None
    duration: int | None
    pubdate: int | None
    tags: list[str]
    view_count: int | None
    like_count: int | None


class VideoListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    videos: list[VideoItem]


@router.get("/favorites", response_model=list[FavoriteFolder])
async def list_favorites(
    service: BilibiliContentService = Depends(get_bilibili_content_service),
) -> list[dict[str, int | str | bool]]:
    try:
        return service.get_favorites()
    except BilibiliContentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/videos/import", response_model=ImportFavoritesResponse)
async def import_favorites(
    request: ImportFavoritesRequest,
    service: BilibiliContentService = Depends(get_bilibili_content_service),
) -> dict[str, str | int | list[int]]:
    try:
        return service.import_favorites(request.folder_ids)
    except BilibiliContentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/videos", response_model=VideoListResponse)
async def list_videos(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    video_repository: VideoRepository = Depends(get_video_repository),
) -> dict[str, int | list[dict[str, object]]]:
    videos, total = video_repository.list_videos(skip=skip, limit=limit)
    return {"total": total, "skip": skip, "limit": limit, "videos": videos}


@router.get("/videos/{bvid}", response_model=VideoItem)
async def get_video(
    bvid: str,
    video_repository: VideoRepository = Depends(get_video_repository),
) -> dict[str, object]:
    video = video_repository.get_by_bvid(bvid)
    if video is None:
        raise HTTPException(status_code=404, detail="video_not_found")
    return video

