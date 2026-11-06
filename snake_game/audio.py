"""Sound: the original mp3s plus a few effects synthesised at start-up (no extra asset files)."""

import math
from array import array

import pygame


def _tone(rate, f0, f1, ms, volume=0.45, shape="sine"):
    """One note gliding from f0 to f1 Hz, with a short attack and a decaying tail."""
    n = max(1, int(rate * ms / 1000))
    out = array("h")
    phase = 0.0
    attack = max(1, int(rate * 0.004))
    for i in range(n):
        t = i / n
        phase += (f0 + (f1 - f0) * t) / rate
        frac = phase % 1.0
        if shape == "square":
            s = 0.55 if frac < 0.5 else -0.55
        elif shape == "triangle":
            s = 4 * abs(frac - 0.5) - 1
        else:
            s = math.sin(math.tau * phase)
        env = min(1.0, i / attack) * (1 - t) ** 1.4
        out.append(int(s * env * volume * 32767))
    return out


def _sequence(rate, notes, shape="triangle", volume=0.45):
    samples = array("h")
    for f0, f1, ms in notes:
        samples.extend(_tone(rate, f0, f1, ms, volume, shape))
    return samples


def _to_sound(samples, channels):
    if channels == 2:
        stereo = array("h")
        for s in samples:
            stereo.append(s)
            stereo.append(s)
        samples = stereo
    return pygame.mixer.Sound(buffer=samples.tobytes())


class Audio:
    """Wraps the mixer. Every method is a harmless no-op if there's no audio device."""

    def __init__(self, asset_dir, music=0.35, sfx=0.8, muted=False):
        self.music_volume = music
        self.sfx_volume = sfx
        self.muted = muted
        self.sounds = {}
        self.ok = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self.ok = True
        except pygame.error:
            return

        self._load_files(asset_dir)
        self._synthesise()
        try:
            pygame.mixer.music.load(str(asset_dir / "bg.mp3"))
            pygame.mixer.music.play(-1)
        except pygame.error:
            pass
        self.apply()

    def _load_files(self, asset_dir):
        for name, filename in (("eat", "eat_sound.mp3"), ("over", "game-over.mp3")):
            try:
                self.sounds[name] = pygame.mixer.Sound(str(asset_dir / filename))
            except (pygame.error, FileNotFoundError):
                pass

    def _synthesise(self):
        rate, fmt, channels = pygame.mixer.get_init()
        if fmt != -16:  # only signed 16-bit is generated; skip effects otherwise
            return
        c = {"C5": 523, "E5": 659, "G5": 784, "C6": 1047, "A4": 440}
        recipes = {
            "bonus": _sequence(rate, [(c["C5"], c["C5"], 70), (c["E5"], c["E5"], 70),
                                      (c["G5"], c["G5"], 70), (c["C6"], c["C6"], 160)]),
            "powerup": _sequence(rate, [(300, 900, 260)], shape="square", volume=0.3),
            "levelup": _sequence(rate, [(c["G5"], c["G5"], 110), (c["G5"], c["G5"], 110),
                                        (c["C6"], c["C6"], 110), (1319, 1319, 300)]),
            "click": _sequence(rate, [(880, 880, 45)], shape="square", volume=0.25),
            "pause": _sequence(rate, [(c["E5"], c["E5"], 70), (c["A4"], c["A4"], 110)]),
            "wall": _sequence(rate, [(160, 90, 140)], shape="square", volume=0.35),
        }
        for name, samples in recipes.items():
            self.sounds[name] = _to_sound(samples, channels)

    # -- control ----------------------------------------------------------- #
    def play(self, name):
        sound = self.sounds.get(name)
        if self.ok and sound and not self.muted:
            sound.set_volume(self.sfx_volume)
            sound.play()

    def apply(self):
        if self.ok:
            pygame.mixer.music.set_volume(0.0 if self.muted else self.music_volume)

    def set_music(self, value):
        self.music_volume = min(1.0, max(0.0, round(value, 2)))
        self.apply()

    def set_sfx(self, value):
        self.sfx_volume = min(1.0, max(0.0, round(value, 2)))

    def toggle_mute(self):
        self.muted = not self.muted
        self.apply()
        return self.muted
