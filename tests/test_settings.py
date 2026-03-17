from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from app.core.config import get_settings, load_settings_from_env


class SettingsTests(TestCase):
    def tearDown(self) -> None:
        get_settings.cache_clear()

    def test_load_settings_defaults(self) -> None:
        settings = load_settings_from_env({})
        self.assertEqual(settings.app_name, "BiliBili Favorites RAG")
        self.assertEqual(settings.port, 8000)
        self.assertEqual(settings.sqlite_path, Path("data/videos.db"))
        self.assertEqual(settings.chroma_path, Path("data/chroma"))

    def test_load_settings_from_environment(self) -> None:
        env = {
            "BILIBILIRAG_APP_NAME": "BiliRag Dev",
            "BILIBILIRAG_PORT": "9000",
            "BILIBILIRAG_APP_ENV": "test",
            "BILIBILIRAG_SQLITE_PATH": "./tmp/test.db",
            "BILIBILIRAG_CHROMA_PATH": "./tmp/chroma",
        }
        settings = load_settings_from_env(env)
        self.assertEqual(settings.app_name, "BiliRag Dev")
        self.assertEqual(settings.port, 9000)
        self.assertEqual(settings.app_env, "test")
        self.assertEqual(settings.sqlite_path, Path("tmp/test.db"))
        self.assertEqual(settings.chroma_path, Path("tmp/chroma"))

    def test_get_settings_uses_cache(self) -> None:
        with patch.dict("os.environ", {"BILIBILIRAG_APP_NAME": "cached"}, clear=True):
            get_settings.cache_clear()
            first = get_settings()
            second = get_settings()
            self.assertIs(first, second)

