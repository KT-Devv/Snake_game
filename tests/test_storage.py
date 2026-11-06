import json
import tempfile
import unittest
from pathlib import Path

from snake_game.storage import DEFAULT_SETTINGS, Storage


class StorageTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_scores_are_per_mode_and_difficulty(self):
        s = Storage(self.dir)
        self.assertTrue(s.submit("classic", "easy", 10))
        self.assertTrue(s.submit("classic", "hard", 4))
        self.assertTrue(s.submit("wrap", "easy", 7))
        self.assertEqual(s.best("classic", "easy"), 10)
        self.assertEqual(s.best("classic", "hard"), 4)
        self.assertEqual(s.best("wrap", "easy"), 7)
        self.assertEqual(s.best("levels", "medium"), 0)

    def test_only_records_count(self):
        s = Storage(self.dir)
        s.submit("classic", "easy", 10)
        self.assertFalse(s.submit("classic", "easy", 10))
        self.assertFalse(s.submit("classic", "easy", 3))
        self.assertEqual(s.best("classic", "easy"), 10)

    def test_scores_persist(self):
        Storage(self.dir).submit("classic", "medium", 21)
        self.assertEqual(Storage(self.dir).best("classic", "medium"), 21)

    def test_legacy_file_migrates_to_classic_easy_once(self):
        legacy = self.dir / "high_score.txt"
        legacy.write_text("24")
        s = Storage(self.dir, legacy_score_file=legacy)
        self.assertEqual(s.best("classic", "easy"), 24)
        self.assertEqual(s.best("classic", "hard"), 0)
        legacy.write_text("99")
        self.assertEqual(Storage(self.dir, legacy_score_file=legacy).best("classic", "easy"), 24)

    def test_corrupt_files_fall_back_to_defaults(self):
        (self.dir / "high_scores.json").write_text("{not json")
        (self.dir / "settings.json").write_text("[1, 2, 3]")
        s = Storage(self.dir)
        self.assertEqual(s.scores, {})
        self.assertEqual(s.settings, DEFAULT_SETTINGS)

    def test_bad_setting_types_are_ignored(self):
        (self.dir / "settings.json").write_text(json.dumps({"music": "loud", "muted": True, "mode": "wrap"}))
        s = Storage(self.dir)
        self.assertEqual(s.settings["music"], DEFAULT_SETTINGS["music"])
        self.assertTrue(s.settings["muted"])
        self.assertEqual(s.settings["mode"], "wrap")

    def test_settings_roundtrip(self):
        s = Storage(self.dir)
        s.settings.update(mode="levels", sfx=0.3)
        s.save_settings()
        again = Storage(self.dir)
        self.assertEqual(again.settings["mode"], "levels")
        self.assertAlmostEqual(again.settings["sfx"], 0.3)

    def test_unwritable_location_does_not_crash(self):
        blocker = self.dir / "blocker"
        blocker.write_text("i am a file, not a folder")
        s = Storage(blocker / "sub")
        s.submit("classic", "easy", 5)  # must not raise
        self.assertEqual(s.best("classic", "easy"), 5)


if __name__ == "__main__":
    unittest.main()
