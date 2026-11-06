"""Build a standalone executable with PyInstaller:   python build.py

Output: dist/Snake (dist/Snake.exe on Windows). Needs `pip install -r requirements-dev.txt`.
Scores and settings of the built game live in a per-user folder, not next to the exe.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    try:
        import PyInstaller.__main__ as pyinstaller
    except ImportError:
        sys.exit("PyInstaller is missing. Run: pip install -r requirements-dev.txt")

    sep = ";" if os.name == "nt" else ":"
    pyinstaller.run([
        str(ROOT / "Snake.py"),
        "--name", "Snake",
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--add-data", f"{ROOT / 'assets'}{sep}assets",
        "--distpath", str(ROOT / "dist"),
        "--workpath", str(ROOT / "build" / "pyinstaller"),
        "--specpath", str(ROOT / "build"),
    ])


if __name__ == "__main__":
    main()
