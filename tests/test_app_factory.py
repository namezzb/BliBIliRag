from pathlib import Path
import tempfile
from unittest import TestCase

from app.core.config import Settings
from app.main import create_app


class AppFactoryTests(TestCase):
    def test_create_app_applies_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings = Settings(
                app_name="BiliRag API",
                app_version="0.2.0",
                data_dir=Path(tmp_dir),
                sqlite_path=Path(tmp_dir) / "videos.db",
                chroma_path=Path(tmp_dir) / "chroma",
            )
            app = create_app(settings)
            self.assertEqual(app.title, "BiliRag API")
            self.assertEqual(app.version, "0.2.0")

    def test_create_app_registers_expected_routes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings = Settings(
                data_dir=Path(tmp_dir),
                sqlite_path=Path(tmp_dir) / "videos.db",
                chroma_path=Path(tmp_dir) / "chroma",
            )
            app = create_app(settings)
            paths = {route.path for route in app.routes}
            self.assertIn("/", paths)
            self.assertIn("/api/health", paths)

