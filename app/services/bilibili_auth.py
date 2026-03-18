from __future__ import annotations

from dataclasses import dataclass
from json import JSONDecodeError
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen
import json

from app.core.config import Settings
from app.repositories import SessionStore

OpenUrlHandler = Callable[..., Any]


class BilibiliAuthError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


@dataclass
class BilibiliAPIClient:
    timeout_seconds: int = 10
    open_url: OpenUrlHandler = urlopen

    def get_json(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        encoded_params = urlencode(params or {})
        full_url = f"{url}?{encoded_params}" if encoded_params else url
        request = Request(full_url, headers=headers or {}, method="GET")
        try:
            with self.open_url(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            raise BilibiliAuthError(
                f"Bilibili request failed with status {exc.code}",
                status_code=502,
            ) from exc
        except URLError as exc:
            raise BilibiliAuthError(
                "Bilibili request failed due to network error",
                status_code=502,
            ) from exc

        try:
            payload = json.loads(body)
        except JSONDecodeError as exc:
            raise BilibiliAuthError("Bilibili response is not valid JSON", 502) from exc

        if payload.get("code") not in (None, 0):
            message = payload.get("message") or payload.get("msg") or "Bilibili API error"
            raise BilibiliAuthError(message, 502)
        return payload


class BilibiliAuthService:
    def __init__(
        self,
        settings: Settings,
        api_client: BilibiliAPIClient,
        session_store: SessionStore,
    ):
        self.settings = settings
        self.api_client = api_client
        self.session_store = session_store

    def generate_qrcode(self) -> dict[str, Any]:
        payload = self.api_client.get_json(
            f"{self.settings.bilibili_passport_base}/x/passport-login/web/qrcode/generate",
            headers=self._base_headers(),
        )
        data = payload.get("data") or {}
        qrcode_key = data.get("qrcode_key")
        qrcode_url = data.get("url")
        if not qrcode_key or not qrcode_url:
            raise BilibiliAuthError("Invalid QR code response from Bilibili", 502)
        return {
            "status": "ok",
            "qrcode_key": str(qrcode_key),
            "qrcode_url": str(qrcode_url),
        }

    def poll_qrcode_status(self, qrcode_key: str) -> dict[str, Any]:
        if not qrcode_key.strip():
            raise BilibiliAuthError("qrcode_key is required", 422)
        payload = self.api_client.get_json(
            f"{self.settings.bilibili_passport_base}/x/passport-login/web/qrcode/poll",
            params={"qrcode_key": qrcode_key},
            headers=self._base_headers(),
        )
        data = payload.get("data") or {}
        auth_code = int(data.get("code", -1))
        auth_message = str(data.get("message", ""))
        callback_url = str(data.get("url", ""))
        cookies = self._extract_cookies(callback_url)
        has_session = bool(cookies)
        if has_session:
            self.session_store.save(cookies)
        return {
            "status": "ok",
            "auth_code": auth_code,
            "auth_message": auth_message,
            "has_session": has_session,
        }

    def get_user_info(self) -> dict[str, Any]:
        cookie_header = self.session_store.build_cookie_header()
        if not cookie_header:
            raise BilibiliAuthError("No bilibili session found, please login first", 401)

        headers = self._base_headers()
        headers["Cookie"] = cookie_header
        payload = self.api_client.get_json(
            f"{self.settings.bilibili_api_base}/x/web-interface/nav",
            headers=headers,
        )
        data = payload.get("data") or {}
        return {
            "is_logged_in": bool(data.get("isLogin", False)),
            "mid": data.get("mid"),
            "uname": data.get("uname"),
        }

    def _base_headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.settings.bilibili_user_agent,
            "Referer": self.settings.bilibili_referer,
            "Origin": self.settings.bilibili_origin,
        }

    @staticmethod
    def _extract_cookies(callback_url: str) -> dict[str, str]:
        if not callback_url:
            return {}
        query = parse_qs(urlparse(callback_url).query, keep_blank_values=False)
        cookies: dict[str, str] = {}
        for key in ("SESSDATA", "bili_jct", "DedeUserID"):
            values = query.get(key)
            if values and values[0]:
                cookies[key] = values[0]
        return cookies

