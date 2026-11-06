"""Constants and tunables. Deliberately free of pygame so the engine stays testable."""

from collections import namedtuple

# --- Board / window ---------------------------------------------------------
CELL = 20
COLS, ROWS = 30, 20
HUD_H = 48
BOARD_W, BOARD_H = COLS * CELL, ROWS * CELL
WIN_W, WIN_H = BOARD_W, BOARD_H + HUD_H
FPS = 60

# --- Directions -------------------------------------------------------------
UP, DOWN, LEFT, RIGHT = (0, -1), (0, 1), (-1, 0), (1, 0)
DIRECTIONS = (UP, DOWN, LEFT, RIGHT)


def opposite(direction):
    return (-direction[0], -direction[1])


# --- Difficulty and game modes ---------------------------------------------
Difficulty = namedtuple("Difficulty", "key label speed color")  # speed = moves per second
DIFFICULTIES = (
    Difficulty("easy", "EASY", 10, (90, 230, 130)),
    Difficulty("medium", "MEDIUM", 15, (255, 220, 100)),
    Difficulty("hard", "HARD", 20, (255, 100, 110)),
)

Mode = namedtuple("Mode", "key label blurb")
MODES = (
    Mode("classic", "CLASSIC", "WALLS ARE DEADLY. EAT, GROW, SURVIVE."),
    Mode("wrap", "WRAP", "THE EDGES LOOP AROUND TO THE OTHER SIDE."),
    Mode("obstacles", "OBSTACLES", "NEW WALLS APPEAR AS YOU EAT."),
    Mode("levels", "LEVELS", "CLEAR HAND-MADE MAPS, ONE AFTER ANOTHER."),
)

SPEED_STEP = 5           # +1 move/second every this many points...
MAX_SPEED_BONUS = 8      # ...up to this much extra

# --- Pickups ----------------------------------------------------------------
BONUS, SLOW, GHOST, DOUBLE = "bonus", "slow", "ghost", "double"
PICKUP_WEIGHTS = {BONUS: 5, SLOW: 2, GHOST: 2, DOUBLE: 2}
PICKUP_LIFETIME_MS = 5000
PICKUP_COOLDOWN_MS = 10000   # quiet time before a pickup can appear
PICKUP_SPAWN_CHANCE = 0.06   # per step, once the cooldown has expired
BONUS_POINTS = 3
EFFECT_DURATION_MS = {SLOW: 6000, GHOST: 5000, DOUBLE: 8000}
SLOW_FACTOR = 0.6            # speed multiplier while SLOW is active

# --- Mode tunables ----------------------------------------------------------
OBSTACLE_EVERY = 4           # foods eaten between new walls (obstacles mode)
MAX_OBSTACLE_CELLS = 48
FOODS_PER_LEVEL = 8          # foods eaten to clear a level (levels mode)

# --- Palette ----------------------------------------------------------------
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (230, 60, 80)
PURPLE = (170, 90, 230)
GOLD = (255, 215, 90)
