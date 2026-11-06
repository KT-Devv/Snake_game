"""Where things live, both when run from source and when frozen by PyInstaller."""

import os
import sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def asset_dir():
    root = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT))
    return root / "assets"


def data_dir():
    """Writable folder for scores and settings.

    SNAKE_DATA_DIR overrides everything. A source checkout keeps its data in the project
    folder; a frozen build can't write beside its exe reliably, so it uses a per-user folder.
    """
    override = os.environ.get("SNAKE_DATA_DIR")
    if override:
        return Path(override)
    if not FROZEN:
        return PROJECT_ROOT
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "SnakeGame"
