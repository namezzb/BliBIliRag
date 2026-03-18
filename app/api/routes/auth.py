from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_bilibili_auth_service
from app.services import BilibiliAuthError, BilibiliAuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


class QRCodeGenerateResponse(BaseModel):
    status: str
    qrcode_key: str
    qrcode_url: str


class QRCodePollResponse(BaseModel):
    status: str
    auth_code: int
    auth_message: str
    has_session: bool


class CurrentUserResponse(BaseModel):
    is_logged_in: bool
    mid: int | None
    uname: str | None


@router.post("/qrcode/generate", response_model=QRCodeGenerateResponse)
async def generate_qrcode(
    service: BilibiliAuthService = Depends(get_bilibili_auth_service),
) -> dict[str, str]:
    try:
        return service.generate_qrcode()
    except BilibiliAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/qrcode/poll", response_model=QRCodePollResponse)
async def poll_qrcode(
    qrcode_key: str = Query(..., min_length=1),
    service: BilibiliAuthService = Depends(get_bilibili_auth_service),
) -> dict[str, str | int | bool]:
    try:
        return service.poll_qrcode_status(qrcode_key)
    except BilibiliAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user(
    service: BilibiliAuthService = Depends(get_bilibili_auth_service),
) -> dict[str, str | int | bool | None]:
    try:
        return service.get_user_info()
    except BilibiliAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

