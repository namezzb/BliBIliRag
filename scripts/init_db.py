from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings
from app.repositories import Database


def main() -> None:
    settings = get_settings()
    settings.ensure_directories()
    database = Database(settings.sqlite_path)
    database.init_schema()
    print(f"Initialized SQLite schema at {settings.sqlite_path}")


if __name__ == "__main__":
    main()
