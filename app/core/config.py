from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Mapping
import os

from pydantic import BaseModel, Field, ValidationError

ENV_PREFIX = "BILIBILIRAG_"


class Settings(BaseModel):
    app_name: str = "BiliBili Favorites RAG"
    app_version: str = "0.1.0"
    app_env: str = "dev"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    data_dir: Path = Field(default=Path("./data"))
    sqlite_path: Path = Field(default=Path("./data/videos.db"))
    chroma_path: Path = Field(default=Path("./data/chroma"))

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self.chroma_path.mkdir(parents=True, exist_ok=True)


def _read_env(environ: Mapping[str, str], key: str, default: str) -> str:
    return environ.get(f"{ENV_PREFIX}{key}", default)


def load_settings_from_env(environ: Mapping[str, str] | None = None) -> Settings:
    current_env = environ if environ is not None else os.environ
    data_dir = Path(_read_env(current_env, "DATA_DIR", "./data"))
    payload = {
        "app_name": _read_env(current_env, "APP_NAME", "BiliBili Favorites RAG"),
        "app_version": _read_env(current_env, "APP_VERSION", "0.1.0"),
        "app_env": _read_env(current_env, "APP_ENV", "dev"),
        "host": _read_env(current_env, "HOST", "0.0.0.0"),
        "port": int(_read_env(current_env, "PORT", "8000")),
        "log_level": _read_env(current_env, "LOG_LEVEL", "INFO").upper(),
        "data_dir": data_dir,
        "sqlite_path": Path(
            _read_env(current_env, "SQLITE_PATH", str(data_dir / "videos.db"))
        ),
        "chroma_path": Path(
            _read_env(current_env, "CHROMA_PATH", str(data_dir / "chroma"))
        ),
    }
    try:
        return Settings(**payload)
    except ValidationError as exc:
        raise ValueError("Invalid application settings") from exc


@lru_cache
def get_settings() -> Settings:
    return load_settings_from_env()

