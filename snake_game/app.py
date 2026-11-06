"""The application: window, state machine (menu / ready / playing / paused / over ...), input."""

import math
import random

import pygame

from . import bot
from .audio import Audio
from .config import (
    BOARD_H, CELL, DIFFICULTIES, FPS, GOLD, HUD_H, MODES, PURPLE, RED, WHITE, WIN_H, WIN_W,
    opposite,
)
from .controls import InputMapper
from .engine import SnakeGame, speed_for
from .maps import level_name
from .paths import PROJECT_ROOT, asset_dir, data_dir
from .render import EFFECT_COLOR, Renderer
from .storage import Storage

DEMO_SPEED = 16           # moves/second for the AI behind the menu
DEMO_RESTART_MS = 1500
VOLUME_STEP = 0.1
DIRECTION_ACTIONS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
EFFECT_TOAST = {"slow": "SLOW MOTION!", "ghost": "GHOST MODE!", "double": "DOUBLE POINTS!"}

MENU_ITEMS = ("play", "mode", "difficulty", "music", "sound", "scores", "watch", "quit")


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color")

    def __init__(self, x, y, color):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(40, 160)
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(angle) * speed, math.sin(angle) * speed
        self.life = self.max_life = random.uniform(0.3, 0.6)
        self.color = color


class App:
    MENU, SCORES, READY, PLAYING, PAUSED, OVER, WATCH = (
        "menu", "scores", "ready", "playing", "paused", "over", "watch")

    def __init__(self, directory=None):
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()

        # The old single-file high score is only imported into the default data folder.
        legacy = PROJECT_ROOT / "high_score.txt" if directory is None else None
        self.storage = Storage(directory or data_dir(), legacy_score_file=legacy)
        s = self.storage.settings

        flags = pygame.SCALED | pygame.RESIZABLE
        if s["fullscreen"]:
            flags |= pygame.FULLSCREEN
        try:
            self.screen = pygame.display.set_mode((WIN_W, WIN_H), flags)
        except pygame.error:  # e.g. a driver without SCALED support
            self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("Snake")
        self.clock = pygame.time.Clock()

        self.renderer = Renderer(self.screen, asset_dir())
        self.audio = Audio(asset_dir(), s["music"], s["sfx"], s["muted"])
        self.mapper = InputMapper()
        self.joysticks = {}
        for i in range(pygame.joystick.get_count()):
            self._add_joystick(i)

        self.mode_index = next((i for i, m in enumerate(MODES) if m.key == s["mode"]), 0)
        self.diff_index = next((i for i, d in enumerate(DIFFICULTIES) if d.key == s["difficulty"]), 0)

        self.state = self.MENU
        self.menu_index = 0
        self.menu_rects = []
        self.game = SnakeGame(mode=self.mode.key)
        self.accumulator = 0.0
        self.play_time_ms = 0
        self.best = 0
        self.new_record = False
        self.run_committed = True
        self.banner = None
        self.particles = []
        self.toasts = []
        self.shake = 0.0
        self.t = 0.0
        self.running = True

        self.demo_count = 0
        self._new_demo()

    # -- properties -------------------------------------------------------- #
    @property
    def mode(self):
        return MODES[self.mode_index]

    @property
    def difficulty(self):
        return DIFFICULTIES[self.diff_index]

    @property
    def label(self):
        return f"{self.mode.label} - {self.difficulty.label}"

    # -- helpers ----------------------------------------------------------- #
    def _add_joystick(self, index):
        try:
            joy = pygame.joystick.Joystick(index)
            self.joysticks[joy.get_instance_id()] = joy
        except pygame.error:
            pass

    def toast(self, msg):
        self.toasts = [[msg, 1.8]]

    def save_settings(self):
        s = self.storage.settings
        s.update(mode=self.mode.key, difficulty=self.difficulty.key, music=self.audio.music_volume,
                 sfx=self.audio.sfx_volume, muted=self.audio.muted)
        self.storage.save_settings()

    def _new_demo(self):
        self.demo = SnakeGame(mode=MODES[self.demo_count % len(MODES)].key)
        self.demo_count += 1
        self.demo_acc = 0.0
        self.demo_wait = 0.0
        self.demo_time = 0

    # -- state transitions ------------------------------------------------- #
    def start_game(self):
        self.game = SnakeGame(mode=self.mode.key)
        self.best = self.storage.best(self.mode.key, self.difficulty.key)
        self.accumulator = 0.0
        self.play_time_ms = 0
        self.new_record = False
        self.run_committed = False
        self.particles.clear()
        self.banner = ("READY", self.mode.label)
        if self.mode.key == "levels":
            self.banner = ("LEVEL 1", level_name(1))
        self.state = self.READY
        self.audio.play("click")

    def commit_run(self):
        if not self.run_committed:
            self.run_committed = True
            self.new_record = self.storage.submit(self.mode.key, self.difficulty.key, self.game.score)

    def end_game(self):
        self.commit_run()
        self.state = self.OVER
        self.shake = 0.35
        self.audio.play("over")

    def go_to_menu(self):
        self.commit_run()
        self.state = self.MENU
        self.audio.play("click")

    def quit(self):
        self.commit_run()
        self.save_settings()
        self.running = False

    # -- events ------------------------------------------------------------ #
    def handle_event(self, event):
        t = event.type
        if t == pygame.QUIT:
            self.quit()
        elif t == pygame.WINDOWFOCUSLOST:
            if self.state == self.PLAYING:
                self.state = self.PAUSED
        elif t == pygame.JOYDEVICEADDED:
            self._add_joystick(event.device_index)
        elif t == pygame.JOYDEVICEREMOVED:
            self.joysticks.pop(getattr(event, "instance_id", None), None)
        elif t == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._click(event.pos)
        else:
            for action in self.mapper.process(event):
                self.dispatch(action)

    def dispatch(self, action):
        """Handle one abstract action (see controls.py)."""
        if action == "mute":
            self.toast("SOUND OFF" if self.audio.toggle_mute() else "SOUND ON")
            self.save_settings()
            return
        if action == "fullscreen":
            pygame.display.toggle_fullscreen()
            self.storage.settings["fullscreen"] = not self.storage.settings["fullscreen"]
            self.storage.save_settings()
            return
        if action in ("vol_up", "vol_down"):
            delta = VOLUME_STEP if action == "vol_up" else -VOLUME_STEP
            self.audio.set_music(self.audio.music_volume + delta)
            self.audio.set_sfx(self.audio.sfx_volume + delta)
            self.toast(f"VOLUME {round(self.audio.music_volume * 100)}%")
            self.save_settings()
            return

        {
            self.MENU: self._act_menu, self.SCORES: self._act_scores, self.READY: self._act_ready,
            self.PLAYING: self._act_playing, self.PAUSED: self._act_paused, self.OVER: self._act_over,
            self.WATCH: self._act_watch,
        }[self.state](action)

    def _click(self, pos):
        if self.state == self.MENU:
            for i, rect in enumerate(self.menu_rects):
                if rect.collidepoint(pos):
                    self.menu_index = i
                    item = MENU_ITEMS[i]
                    if item in ("mode", "difficulty", "music", "sound"):
                        left = pos[0] < rect.centerx + 40
                        self._menu_adjust(item, -1 if left else 1)
                    else:
                        self._act_menu("confirm")
                    return
        elif self.state == self.PAUSED:
            self.state = self.PLAYING
        elif self.state == self.OVER:
            self.start_game()
        elif self.state in (self.SCORES, self.WATCH):
            self.go_to_menu()

    # -- per-state actions ------------------------------------------------- #
    def _act_menu(self, action):
        item = MENU_ITEMS[self.menu_index]
        n = len(MENU_ITEMS)
        if action == "up":
            self.menu_index = (self.menu_index - 1) % n
        elif action == "down":
            self.menu_index = (self.menu_index + 1) % n
        elif action in ("left", "right"):
            self._menu_adjust(item, -1 if action == "left" else 1)
        elif action == "confirm":
            if item == "play":
                self.start_game()
            elif item in ("mode", "difficulty", "music", "sound"):
                self._menu_adjust(item, 1)
            elif item == "scores":
                self.state = self.SCORES
            elif item == "watch":
                self._new_demo()
                self.state = self.WATCH
            elif item == "quit":
                self.quit()
        elif action == "back":
            self.quit()

    def _menu_adjust(self, item, step):
        if item == "mode":
            self.mode_index = (self.mode_index + step) % len(MODES)
        elif item == "difficulty":
            self.diff_index = (self.diff_index + step) % len(DIFFICULTIES)
        elif item == "music":
            self.audio.set_music(self.audio.music_volume + step * VOLUME_STEP)
        elif item == "sound":
            self.audio.set_sfx(self.audio.sfx_volume + step * VOLUME_STEP)
        else:
            return
        self.audio.play("click")
        self.save_settings()

    def _act_scores(self, action):
        if action in ("back", "confirm", "menu"):
            self.state = self.MENU
            self.audio.play("click")

    def _act_watch(self, action):
        if action not in ("mute",):
            self.state = self.MENU

    def _act_ready(self, action):
        if action in DIRECTION_ACTIONS:
            d = DIRECTION_ACTIONS[action]
            if d != opposite(self.game.direction):
                self.game.queue_turn(d)
                self.accumulator = 0.0
                self.banner = None
                self.state = self.PLAYING
        elif action in ("back", "menu"):
            self.go_to_menu()

    def _act_playing(self, action):
        if action in DIRECTION_ACTIONS:
            self.game.queue_turn(DIRECTION_ACTIONS[action])
        elif action in ("pause", "back", "confirm"):
            self.state = self.PAUSED
            self.audio.play("pause")

    def _act_paused(self, action):
        if action in ("pause", "back", "confirm"):
            self.state = self.PLAYING
            self.audio.play("pause")
        elif action == "menu":
            self.go_to_menu()

    def _act_over(self, action):
        if action == "confirm":
            self.start_game()
        elif action in ("back", "menu"):
            self.go_to_menu()

    # -- update ------------------------------------------------------------ #
    def interval_ms(self, game, base_speed):
        return 1000 / (speed_for(base_speed, game.score) * game.speed_multiplier)

    def update(self, dt_ms):
        dt_ms = min(dt_ms, 100)  # a dragged window or a breakpoint must not fast-forward the snake
        dt = dt_ms / 1000
        self.t += dt
        self.shake = max(0.0, self.shake - dt)
        for p in self.particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.life -= dt
        self.particles = [p for p in self.particles if p.life > 0]
        for toast in self.toasts:
            toast[1] -= dt
        self.toasts = [x for x in self.toasts if x[1] > 0]

        if self.state == self.PLAYING:
            self._advance_game(dt_ms)
        elif self.state in (self.MENU, self.SCORES, self.WATCH):
            self._advance_demo(dt_ms)

    def _advance_game(self, dt_ms):
        game = self.game
        self.play_time_ms += dt_ms
        self.accumulator += dt_ms
        while self.state == self.PLAYING:
            interval = self.interval_ms(game, self.difficulty.speed)
            if self.accumulator < interval:
                break
            self.accumulator -= interval
            for event in game.step(interval):
                self._on_event(event)

    def _advance_demo(self, dt_ms):
        demo = self.demo
        if not demo.alive:
            self.demo_wait += dt_ms
            if self.demo_wait >= DEMO_RESTART_MS:
                self._new_demo()
            return
        self.demo_time += dt_ms
        self.demo_acc += dt_ms
        interval = 1000 / DEMO_SPEED
        while self.demo_acc >= interval and demo.alive:
            self.demo_acc -= interval
            bot.play_step(demo, interval)

    def _on_event(self, event):
        game = self.game
        hx, hy = game.snake[0]
        px, py = hx * CELL + CELL // 2, hy * CELL + CELL // 2

        def burst(color, count):
            self.particles.extend(Particle(px, py, color) for _ in range(count))

        if event == "eat":
            self.audio.play("eat")
            burst(RED, 10)
        elif event.startswith("pickup:"):
            kind = event.split(":")[1]
            if kind == "bonus":
                self.audio.play("bonus")
                burst(PURPLE, 22)
                self.toast("BONUS!")
            else:
                self.audio.play("powerup")
                burst(EFFECT_COLOR[kind], 18)
                self.toast(EFFECT_TOAST[kind])
        elif event == "obstacle":
            self.audio.play("wall")
            self.toast("NEW WALL!")
        elif event == "level":
            self.audio.play("levelup")
            self.particles.clear()
            self.banner = (f"LEVEL {game.level}", level_name(game.level))
            self.accumulator = 0.0
            self.state = self.READY
        elif event in ("dead", "win"):
            self.end_game()

    # -- drawing ----------------------------------------------------------- #
    def draw(self):
        r = self.renderer
        r.background()
        if self.state in (self.MENU, self.SCORES, self.WATCH):
            self._draw_demo()
        else:
            self._draw_game()
        for msg, _ in self.toasts:
            r.toast(msg, HUD_H + BOARD_H - 26)
        pygame.display.flip()

    def _draw_demo(self):
        r = self.renderer
        demo = self.demo
        interval = 1000 / DEMO_SPEED
        mode = next(m for m in MODES if m.key == demo.mode)
        r.board(demo, self.demo_acc / interval, self.t, self.difficulty.color, dead=not demo.alive)
        if self.state == self.WATCH:  # menus cover the HUD area, so only show it when watching
            r.hud(demo, f"AI - {mode.label}", self.demo_time, 0, self.difficulty.color)

        if self.state == self.MENU:
            self.menu_rects = r.menu(self._menu_rows(), self.menu_index, self.t, self.mode.blurb,
                                     "ARROWS + ENTER    M MUTE    F11 FULLSCREEN")
        elif self.state == self.SCORES:
            r.scores_table(self.storage.best, self.t)
        else:
            r.toast("AI PLAYING - PRESS ANY KEY", HUD_H + BOARD_H - 26)

    def _menu_rows(self):
        a = self.audio
        accent = {"mode": WHITE, "difficulty": self.difficulty.color}
        return [
            ("PLAY", None, None, GOLD),
            ("MODE", self.mode.label, None, accent["mode"]),
            ("DIFFICULTY", self.difficulty.label, None, accent["difficulty"]),
            ("MUSIC", None, 0.0 if a.muted else a.music_volume, WHITE),
            ("SOUND FX", None, 0.0 if a.muted else a.sfx_volume, WHITE),
            ("HIGH SCORES", None, None, WHITE),
            ("WATCH AI", None, None, WHITE),
            ("QUIT", None, None, WHITE),
        ]

    def _draw_game(self):
        r = self.renderer
        game = self.game
        offset = (0, 0)
        if self.shake > 0:
            m = int(self.shake * 14)
            offset = (random.randint(-m, m), random.randint(-m, m))
        interval = self.interval_ms(game, self.difficulty.speed)
        alpha = self.accumulator / interval if self.state == self.PLAYING else 1.0
        r.board(game, alpha, self.t, self.difficulty.color, self.particles, offset,
                dead=self.state == self.OVER)
        r.hud(game, self.label, self.play_time_ms, self.best, self.difficulty.color)

        if self.state == self.READY and self.banner:
            r.banner(*self.banner, self.t)
        elif self.state == self.PAUSED:
            r.overlay("PAUSED", [("P / SPACE  RESUME", (225, 220, 245)), ("Q  MENU", (225, 220, 245))])
        elif self.state == self.OVER:
            self._draw_game_over()
        if self.audio.muted:
            r.text("MUTED", r.font_tiny, (255, 150, 150), topleft=(8, HUD_H + 6))

    def _draw_game_over(self):
        game = self.game
        soft = (225, 220, 245)
        lines = [(f"SCORE {game.score}", WHITE)]
        if self.new_record:
            lines.append(("NEW BEST!", GOLD))
        else:
            lines.append((f"BEST {max(self.best, game.score)}", GOLD))
        lines.append(("ENTER  PLAY AGAIN", soft))
        lines.append(("ESC  MENU", soft))
        self.renderer.overlay("YOU WIN!" if game.won else "GAME OVER", lines,
                              GOLD if game.won else RED, backdrop=True)

    # -- main loop --------------------------------------------------------- #
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS)
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.draw()
        pygame.quit()


def selftest():
    """Start the app headlessly, run a few frames and verify assets loaded.

    `python Snake.py --selftest` (or `Snake.exe --selftest`). Exit code 0 = healthy.
    Used to smoke-test a PyInstaller build without opening a window.
    """
    import os
    import tempfile
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    app = App(directory=tempfile.mkdtemp(prefix="snake-selftest-"))
    try:
        for _ in range(30):
            app.update(16)
            app.draw()
        audio_ok = not app.audio.ok or {"eat", "over", "bonus"} <= set(app.audio.sounds)
        return 0 if app.renderer.assets_ok and audio_ok else 2
    finally:
        pygame.quit()


def main(argv=None):
    import sys
    argv = sys.argv[1:] if argv is None else argv
    if "--selftest" in argv:
        sys.exit(selftest())
    App().run()
