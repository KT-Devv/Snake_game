"""High scores (per mode and difficulty) and user settings, stored as JSON."""

import json
import os
import tempfile
from pathlib import Path

DEFAULT_SETTINGS = {
    "music": 0.35,
    "sfx": 0.8,
    "muted": False,
    "fullscreen": False,
    "mode": "classic",
    "difficulty": "easy",
}


def _read_json(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_json(path, data):
    """Atomic write, so a crash mid-save can't corrupt the file. Failures are non-fatal."""
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
        os.replace(tmp, path)
    except OSError:
        pass


class Storage:
    def __init__(self, directory, legacy_score_file=None):
        self.dir = Path(directory)
        self.scores_path = self.dir / "high_scores.json"
        self.settings_path = self.dir / "settings.json"

        self.scores = {k: int(v) for k, v in _read_json(self.scores_path).items()
                       if isinstance(v, int) and v >= 0}
        if not self.scores_path.exists() and legacy_score_file:
            self._migrate_legacy(Path(legacy_score_file))

        self.settings = dict(DEFAULT_SETTINGS)
        for key, default in DEFAULT_SETTINGS.items():
            value = _read_json(self.settings_path).get(key, default)
            if type(value) is type(default) or (isinstance(default, float) and isinstance(value, int)):
                self.settings[key] = value

    def _migrate_legacy(self, path):
        """The old single high_score.txt becomes Classic/Easy: the lowest bucket, so it
        never overstates a record set on a harder setting."""
        try:
            value = int(path.read_text().strip())
        except (OSError, ValueError):
            return
        if value > 0:
            self.scores[self.key("classic", "easy")] = value
            self.save_scores()

    @staticmethod
    def key(mode, difficulty):
        return f"{mode}:{difficulty}"

    # -- scores ------------------------------------------------------------ #
    def best(self, mode, difficulty):
        return self.scores.get(self.key(mode, difficulty), 0)

    def submit(self, mode, difficulty, score):
        """Record a finished run. Returns True if it set a new record."""
        if score > self.best(mode, difficulty):
            self.scores[self.key(mode, difficulty)] = int(score)
            self.save_scores()
            return True
        return False

    def save_scores(self):
        _write_json(self.scores_path, self.scores)

    # -- settings ---------------------------------------------------------- #
    def save_settings(self):
        _write_json(self.settings_path, self.settings)
