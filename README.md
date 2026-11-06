# Snake

A polished take on the classic, built with Python and Pygame: four game modes, power-ups, hand-made levels,
smooth movement, a self-playing AI, gamepad and touch support, and per-mode high scores.

## Play

Requires Python 3.10+.

```bash
pip install -r requirements.txt
python Snake.py
```

## Game modes

| Mode | What's different |
| --- | --- |
| **Classic** | Walls are deadly. |
| **Wrap** | The edges loop around to the opposite side. |
| **Obstacles** | A new wall appears every 4 foods. Walls never trap you: open space always stays connected. |
| **Levels** | Eat 8 foods to clear a hand-made map and move to the next one. |

Each mode has three difficulties (Easy / Medium / Hard) that set the starting speed. The snake speeds up as your score climbs.
High scores are tracked separately for every mode and difficulty (12 in total).

## Power-ups

An item occasionally appears and fades after 5 seconds (a ring shows the time left).

| Item | Effect |
| --- | --- |
| Purple orb | **Bonus**: +3 points and +3 length |
| `S` | **Slow motion** for 6 s |
| `G` | **Ghost** for 5 s: pass through yourself and walls (not the board edge). It won't wear off while you're inside something. |
| `x2` | **Double points** for 8 s |

## Controls

| Input | Action |
| --- | --- |
| Arrow keys / WASD | Steer (the snake waits for your first move) |
| `Enter` / `Space` | Confirm |
| `P` / `Space` / `Esc` | Pause |
| `Q` | Back to the menu (when paused / game over) |
| `M` | Mute |
| `-` / `=` | Volume down / up |
| `F11` | Fullscreen |
| **Gamepad** | D-pad or left stick steers · A confirm · B back · Start pause · Back menu |
| **Touch** | Swipe to steer; tap menu items |
| **Mouse** | Click menu items |

The main menu also has **Watch AI**, which plays the game by itself using breadth-first search with a "can I still reach my tail?" safety check.
The same bot plays behind the menu.

## Project layout

```
Snake.py            entry point (python Snake.py, or python -m snake_game)
snake_game/
  config.py         constants and tunables
  engine.py         pure game rules (no pygame): movement, modes, pickups, obstacles
  maps.py           hand-made LEVELS maps
  bot.py            the AI player
  storage.py        per-mode high scores + settings (JSON, atomic writes)
  audio.py          sound manager; extra effects are synthesised at start-up
  controls.py       keyboard / gamepad / touch -> abstract actions
  render.py         all drawing, including smooth interpolated movement
  app.py            window, menus and the state machine
assets/             images, music, sound effects, font
tests/              unit + headless integration tests
build.py            PyInstaller build script
```

Scores and settings are saved to `high_scores.json` / `settings.json` in the project folder
(or `%APPDATA%\SnakeGame` for a built exe). Set `SNAKE_DATA_DIR` to put them elsewhere.
An old `high_score.txt` is imported once, as the Classic/Easy record.

## Development

```bash
pip install -r requirements-dev.txt
python -m unittest discover -s tests -t . -v     # headless; touches no real data
python -m pyflakes snake_game tests Snake.py build.py
python Snake.py --selftest                       # starts the app headlessly, checks assets, exits 0 if OK
```

### Standalone executable

```bash
python build.py          # -> dist/Snake.exe (or dist/Snake on macOS/Linux)
```

CI (`.github/workflows/ci.yml`) runs lint and the test suite on Ubuntu and Windows for Python 3.10, 3.12 and 3.13.
