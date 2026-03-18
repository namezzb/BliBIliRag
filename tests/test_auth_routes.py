from __future__ import annotations

from unittest import IsolatedAsyncioTestCase

from fastapi import HTTPException

from app.api.routes.auth import generate_qrcode, get_current_user, poll_qrcode
from app.services import BilibiliAuthError


class _FakeAuthService:
    def __init__(self) -> None:
        self.should_fail = False

    def generate_qrcode(self):  # noqa: ANN201
        if self.should_fail:
            raise BilibiliAuthError("bad request", 400)
        return {
            "status": "ok",
            "qrcode_key": "k1",
            "qrcode_url": "https://example.com",
        }

    def poll_qrcode_status(self, qrcode_key: str):  # noqa: ANN201
        if self.should_fail:
            raise BilibiliAuthError("poll failed", 502)
        return {
            "status": "ok",
            "auth_code": 0,
            "auth_message": f"done:{qrcode_key}",
            "has_session": True,
        }

    def get_user_info(self):  # noqa: ANN201
        if self.should_fail:
            raise BilibiliAuthError("unauthorized", 401)
        return {"is_logged_in": True, "mid": 1, "uname": "u1"}


class AuthRouteTests(IsolatedAsyncioTestCase):
    async def test_generate_qrcode_route(self) -> None:
        service = _FakeAuthService()
        payload = await generate_qrcode(service=service)
        self.assertEqual(payload["qrcode_key"], "k1")

    async def test_poll_qrcode_route(self) -> None:
        service = _FakeAuthService()
        payload = await poll_qrcode(qrcode_key="abc", service=service)
        self.assertEqual(payload["auth_message"], "done:abc")
        self.assertTrue(payload["has_session"])

    async def test_get_current_user_route(self) -> None:
        service = _FakeAuthService()
        payload = await get_current_user(service=service)
        self.assertTrue(payload["is_logged_in"])
        self.assertEqual(payload["mid"], 1)

    async def test_generate_qrcode_route_maps_errors(self) -> None:
        service = _FakeAuthService()
        service.should_fail = True
        with self.assertRaises(HTTPException) as context:
            await generate_qrcode(service=service)
        self.assertEqual(context.exception.status_code, 400)

