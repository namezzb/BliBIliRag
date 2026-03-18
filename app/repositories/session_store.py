from __future__ import annotations

from pathlib import Path
import json
from typing import Any

COOKIE_KEYS = ("SESSDATA", "bili_jct", "DedeUserID")


class SessionStore:
    def __init__(self, session_file: str | Path):
        self.session_file = Path(session_file)
        self.session_file.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, str]:
        if not self.session_file.exists():
            return {}
        raw_text = self.session_file.read_text(encoding="utf-8").strip()
        if not raw_text:
            return {}
        payload: dict[str, Any] = json.loads(raw_text)
        return {k: str(v) for k, v in payload.items() if v is not None}

    def save(self, cookies: dict[str, str]) -> dict[str, str]:
        existing = self.load()
        for key in COOKIE_KEYS:
            value = cookies.get(key)
            if value:
                existing[key] = value
        self.session_file.write_text(
            json.dumps(existing, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
        return existing

    def build_cookie_header(self) -> str:
        cookies = self.load()
        pairs = [f"{key}={cookies[key]}" for key in COOKIE_KEYS if cookies.get(key)]
        return "; ".join(pairs)

