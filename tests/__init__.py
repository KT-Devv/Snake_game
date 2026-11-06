"""Tests run headless: dummy video/audio drivers, and a throwaway data directory so the
suite never touches real scores or settings."""

import os
import tempfile
import warnings

# SDL's dummy video driver has no GPU renderer, so pygame.SCALED warns; it's irrelevant here.
warnings.filterwarnings("ignore", message="no fast renderer available")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ["SNAKE_DATA_DIR"] = tempfile.mkdtemp(prefix="snake-tests-")
