"""Drive the real App headlessly through its screens."""

import tempfile
import unittest

import pygame

from snake_game.app import MENU_ITEMS, App
from snake_game.config import FOODS_PER_LEVEL, MODES


class AppTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.app = App(directory=self._tmp.name)

    def tearDown(self):
        pygame.quit()
        self._tmp.cleanup()

    # helpers
    def act(self, *actions):
        for a in actions:
            self.app.dispatch(a)

    def select(self, item):
        self.app.menu_index = MENU_ITEMS.index(item)

    def run_frames(self, n, dt=16):
        for _ in range(n):
            self.app.update(dt)
            self.app.draw()

    def play_until_over(self, frames=2000):
        for _ in range(frames):
            self.app.update(16)
            self.app.draw()
            if self.app.state == App.OVER:
                return
        self.fail("game never ended")

    # tests
    def test_full_flow_menu_to_game_over_and_restart(self):
        a = self.app
        self.assertEqual(a.state, App.MENU)
        self.run_frames(30)                       # demo bot runs behind the menu
        self.select("play")
        self.act("confirm")
        self.assertEqual(a.state, App.READY)
        self.run_frames(10)
        self.assertEqual(a.game.snake[0], (15, 10), "must wait for the first direction")
        self.act("right")
        self.assertEqual(a.state, App.PLAYING)

        self.act("pause")
        self.assertEqual(a.state, App.PAUSED)
        self.act("pause")
        self.assertEqual(a.state, App.PLAYING)

        self.play_until_over()
        self.act("confirm")
        self.assertEqual(a.state, App.READY)
        self.assertEqual(a.game.score, 0)
        self.act("back")
        self.assertEqual(a.state, App.MENU)

    def test_reverse_is_not_a_valid_first_move(self):
        self.select("play")
        self.act("confirm", "left")
        self.assertEqual(self.app.state, App.READY)

    def test_mode_and_difficulty_cycle_and_persist(self):
        a = self.app
        self.select("mode")
        self.act("right")
        self.assertEqual(a.mode.key, MODES[1].key)
        self.select("difficulty")
        self.act("left")
        self.assertEqual(a.difficulty.key, "hard")
        again = App(directory=self._tmp.name)
        self.assertEqual(again.mode.key, MODES[1].key)
        self.assertEqual(again.difficulty.key, "hard")

    def test_scores_are_saved_per_setting_and_flagged_as_records(self):
        a = self.app
        a.mode_index, a.diff_index = 1, 2         # wrap / hard
        a.start_game()
        a.game.score = 7
        a.end_game()
        self.assertTrue(a.new_record)
        self.assertEqual(a.storage.best("wrap", "hard"), 7)
        self.assertEqual(a.storage.best("classic", "easy"), 0)

    def test_quitting_mid_run_still_saves_the_score(self):
        a = self.app
        a.start_game()
        a.game.score = 5
        a.quit()
        self.assertEqual(a.storage.best("classic", "easy"), 5)
        self.assertFalse(a.running)

    def test_scores_and_watch_screens(self):
        self.select("scores")
        self.act("confirm")
        self.assertEqual(self.app.state, App.SCORES)
        self.run_frames(5)
        self.act("back")
        self.select("watch")
        self.act("confirm")
        self.assertEqual(self.app.state, App.WATCH)
        self.run_frames(120)
        self.act("confirm")
        self.assertEqual(self.app.state, App.MENU)

    def test_volume_and_mute_controls(self):
        a = self.app
        a.audio.set_music(0.5)
        self.act("vol_up")
        self.assertAlmostEqual(a.audio.music_volume, 0.6)
        self.act("vol_down", "vol_down", "vol_down", "vol_down", "vol_down", "vol_down", "vol_down")
        self.assertEqual(a.audio.music_volume, 0.0)
        before = a.audio.muted
        self.act("mute")
        self.assertNotEqual(a.audio.muted, before)

    def test_levels_mode_shows_level_banner_after_clearing(self):
        a = self.app
        a.mode_index = [m.key for m in MODES].index("levels")
        a.start_game()
        self.act("right")
        for _ in range(FOODS_PER_LEVEL):
            hx, hy = a.game.snake[0]
            a.game.food = (hx + 1, hy)
            for ev in a.game.step(60):
                a._on_event(ev)
        self.assertEqual(a.state, App.READY)
        self.assertEqual(a.banner[0], "LEVEL 2")
        self.run_frames(5)

    def test_every_pickup_draws(self):
        from snake_game.engine import Pickup
        a = self.app
        a.start_game()
        self.act("right")
        for kind in ("bonus", "slow", "ghost", "double"):
            a.game.pickup = Pickup(kind, (3, 3), 4000)
            if kind != "bonus":
                a.game.effects[kind] = 3000
            self.run_frames(3)
        self.assertEqual(a.state, App.PLAYING)

    def test_mouse_click_selects_menu_item(self):
        a = self.app
        self.run_frames(2)
        rect = a.menu_rects[MENU_ITEMS.index("scores")]
        a.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))
        self.assertEqual(a.state, App.SCORES)

    def test_focus_loss_pauses(self):
        self.select("play")
        self.act("confirm", "right")
        self.app.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertEqual(self.app.state, App.PAUSED)

    def test_snake_never_moves_faster_than_its_interval(self):
        """A long frame (window drag) must not fast-forward the game."""
        a = self.app
        a.start_game()
        self.act("right")
        head = a.game.snake[0]
        a.update(5000)
        moved = abs(a.game.snake[0][0] - head[0]) + abs(a.game.snake[0][1] - head[1])
        self.assertLessEqual(moved, 3)


class SelfTestTests(unittest.TestCase):
    def test_selftest_passes_when_assets_are_present(self):
        from snake_game.app import selftest
        self.assertEqual(selftest(), 0)


if __name__ == "__main__":
    unittest.main()
