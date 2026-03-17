from pathlib import Path
import tempfile
from unittest import IsolatedAsyncioTestCase

from fastapi import FastAPI
from fastapi.routing import APIRoute

from app.core.config import Settings
from app.main import create_app


def get_route(app: FastAPI, path: str, method: str) -> APIRoute:
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return route
    raise AssertionError(f"Route not found: {method} {path}")


class HealthRoutesTests(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        self.settings = Settings(
            app_name="BiliRag Test",
            app_version="9.9.9",
            app_env="test",
            data_dir=Path(tmp_dir.name),
            sqlite_path=Path(tmp_dir.name) / "videos.db",
            chroma_path=Path(tmp_dir.name) / "chroma",
        )
        self.app = create_app(self.settings)

    async def test_root_handler_payload(self) -> None:
        route = get_route(self.app, "/", "GET")
        payload = await route.endpoint(settings=self.settings)
        self.assertEqual(payload["name"], "BiliRag Test")
        self.assertEqual(payload["version"], "9.9.9")
        self.assertEqual(payload["status"], "ok")

    async def test_health_handler_payload(self) -> None:
        route = get_route(self.app, "/api/health", "GET")
        payload = await route.endpoint(settings=self.settings)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["environment"], "test")

