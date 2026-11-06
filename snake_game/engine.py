"""Pure game rules: snake, food, pickups, modes. No pygame, so it is fully unit-testable.

step() returns a list of event strings the UI reacts to:
    "eat", "pickup:<kind>", "obstacle", "level", "dead", "win"
"""

import random
from collections import deque
from dataclasses import dataclass

from .config import (
    BONUS, BONUS_POINTS, COLS, DIRECTIONS, DOUBLE, EFFECT_DURATION_MS, FOODS_PER_LEVEL,
    GHOST, MAX_OBSTACLE_CELLS, MAX_SPEED_BONUS, OBSTACLE_EVERY, PICKUP_COOLDOWN_MS,
    PICKUP_LIFETIME_MS, PICKUP_SPAWN_CHANCE, PICKUP_WEIGHTS, RIGHT, ROWS, SLOW,
    SLOW_FACTOR, SPEED_STEP, opposite,
)
from .maps import level_cells


@dataclass
class Pickup:
    kind: str
    pos: tuple
    left_ms: float


def speed_for(base_speed, score):
    """Moves per second: the base speed plus one per SPEED_STEP points, capped."""
    return base_speed + min(score // SPEED_STEP, MAX_SPEED_BONUS)


class SnakeGame:
    def __init__(self, cols=COLS, rows=ROWS, mode="classic", rng=None, pickups=True):
        self.cols = cols
        self.rows = rows
        self.mode = mode
        self.wrap = mode == "wrap"
        self.rng = rng or random.Random()
        self.pickups_enabled = pickups
        self.reset()

    # -- setup ------------------------------------------------------------- #
    def reset(self):
        self.score = 0
        self.foods_eaten = 0
        self.level = 1
        self.alive = True
        self.won = False
        self.effects = {}                 # kind -> ms left
        self.pickup = None
        self.pickup_cooldown = PICKUP_COOLDOWN_MS
        self.obstacles = set()
        if self.mode == "levels":
            self.obstacles = level_cells(1, self.cols, self.rows)
        self.food = None
        self._spawn_snake()
        self.food = self._random_free_cell()

    def _spawn_snake(self):
        cx, cy = self.cols // 2, self.rows // 2
        self.snake = deque([(cx, cy), (cx - 1, cy), (cx - 2, cy)])  # head first
        self.prev_snake = list(self.snake)  # last step's cells, for smooth rendering
        self.direction = RIGHT
        self.turns = deque()                # buffered turns so quick taps aren't lost
        self.pending_growth = 0

    # -- input ------------------------------------------------------------- #
    def queue_turn(self, direction):
        """Buffer a turn. Reversals and repeats (vs. the last buffered turn) are ignored."""
        last = self.turns[-1] if self.turns else self.direction
        if direction == last or direction == opposite(last):
            return
        if len(self.turns) < 3:
            self.turns.append(direction)

    # -- queries ----------------------------------------------------------- #
    @property
    def length(self):
        return len(self.snake)

    @property
    def speed_multiplier(self):
        return SLOW_FACTOR if SLOW in self.effects else 1.0

    def neighbors(self, cell):
        """Yield (cell, direction) for each in-bounds (or wrapped) neighbour."""
        x, y = cell
        for d in DIRECTIONS:
            nx, ny = x + d[0], y + d[1]
            if self.wrap:
                nx %= self.cols
                ny %= self.rows
            elif not (0 <= nx < self.cols and 0 <= ny < self.rows):
                continue
            yield (nx, ny), d

    # -- simulation -------------------------------------------------------- #
    def step(self, dt_ms=0):
        """Advance one move. dt_ms is the real time this step represents (drives timers)."""
        if not self.alive:
            return []

        if self.turns:
            self.direction = self.turns.popleft()

        hx, hy = self.snake[0]
        nx, ny = hx + self.direction[0], hy + self.direction[1]
        if self.wrap:
            nx %= self.cols
            ny %= self.rows
        elif not (0 <= nx < self.cols and 0 <= ny < self.rows):
            self.alive = False
            return ["dead"]
        new_head = (nx, ny)

        pickup = self.pickup if self.pickup and self.pickup.pos == new_head else None
        eats_food = new_head == self.food
        grows = self.pending_growth > 0 or eats_food or (pickup is not None and pickup.kind == BONUS)

        if GHOST not in self.effects:
            # The tail cell is vacated this step unless we're growing, so entering it is safe.
            hits_body = new_head in self.snake and not (new_head == self.snake[-1] and not grows)
            if hits_body or new_head in self.obstacles:
                self.alive = False
                return ["dead"]

        self.prev_snake = list(self.snake)
        events = []
        mult = 2 if DOUBLE in self.effects else 1

        if eats_food:
            self.score += mult
            self.pending_growth += 1
            self.foods_eaten += 1
            events.append("eat")
        if pickup is not None:
            self.pickup = None
            self.pickup_cooldown = PICKUP_COOLDOWN_MS
            if pickup.kind == BONUS:
                self.score += BONUS_POINTS * mult
                self.pending_growth += BONUS_POINTS
            else:
                self.effects[pickup.kind] = EFFECT_DURATION_MS[pickup.kind]
            events.append("pickup:" + pickup.kind)

        self.snake.appendleft(new_head)
        if self.pending_growth > 0:
            self.pending_growth -= 1  # keep the tail this step
        else:
            self.snake.pop()

        if eats_food:
            if self.mode == "levels" and self.foods_eaten % FOODS_PER_LEVEL == 0:
                self._next_level()
                return events + ["level"]
            self.food = self._random_free_cell()
            if self.food is None:
                self.alive = False
                self.won = True
                return events + ["win"]
            if self.mode == "obstacles" and self.foods_eaten % OBSTACLE_EVERY == 0:
                if self._add_obstacle():
                    events.append("obstacle")

        self._tick_timers(dt_ms)
        return events

    def _next_level(self):
        self.level += 1
        self.obstacles = level_cells(self.level, self.cols, self.rows)
        self.pickup = None
        self.pickup_cooldown = PICKUP_COOLDOWN_MS
        self.effects.clear()
        self._spawn_snake()
        self.food = None
        self.food = self._random_free_cell()

    # -- timers and pickups ------------------------------------------------ #
    def _tick_timers(self, dt_ms):
        for kind in list(self.effects):
            self.effects[kind] -= dt_ms
            if self.effects[kind] <= 0:
                if kind == GHOST and self._head_overlaps_solid():
                    self.effects[kind] = 1  # don't drop the ghost while inside a wall or ourselves
                else:
                    del self.effects[kind]

        if self.pickup is not None:
            self.pickup.left_ms -= dt_ms
            if self.pickup.left_ms <= 0:
                self.pickup = None
                self.pickup_cooldown = PICKUP_COOLDOWN_MS
        elif self.pickups_enabled:
            self.pickup_cooldown -= dt_ms
            if self.pickup_cooldown <= 0 and self.rng.random() < PICKUP_SPAWN_CHANCE:
                cell = self._random_free_cell()
                if cell is not None:
                    kinds = list(PICKUP_WEIGHTS)
                    kind = self.rng.choices(kinds, [PICKUP_WEIGHTS[k] for k in kinds])[0]
                    self.pickup = Pickup(kind, cell, PICKUP_LIFETIME_MS)

    def _head_overlaps_solid(self):
        head = self.snake[0]
        return head in self.obstacles or head in list(self.snake)[1:]

    # -- obstacles mode ---------------------------------------------------- #
    def _add_obstacle(self):
        """Drop a short wall somewhere safe. Never traps the player: open space stays connected."""
        if len(self.obstacles) + 3 > MAX_OBSTACLE_CELLS:
            return False
        occupied = set(self.snake) | self.obstacles
        if self.food:
            occupied.add(self.food)
        if self.pickup:
            occupied.add(self.pickup.pos)
        hx, hy = self.snake[0]
        for _ in range(60):
            length = self.rng.choice((2, 3))
            horizontal = self.rng.random() < 0.5
            x = self.rng.randrange(self.cols - (length - 1 if horizontal else 0))
            y = self.rng.randrange(self.rows - (0 if horizontal else length - 1))
            cells = [(x + i, y) if horizontal else (x, y + i) for i in range(length)]
            if any(c in occupied for c in cells):
                continue
            if any(abs(c[0] - hx) + abs(c[1] - hy) <= 5 for c in cells):
                continue  # not right in the player's face
            trial = self.obstacles | set(cells)
            if self._open_space_connected(trial):
                self.obstacles = trial
                return True
        return False

    def _open_space_connected(self, walls):
        free = {(x, y) for x in range(self.cols) for y in range(self.rows)} - walls
        if not free:
            return False
        start = next(iter(free))
        seen = {start}
        stack = [start]
        while stack:
            cell = stack.pop()
            for nxt, _ in self.neighbors(cell):
                if nxt in free and nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        return len(seen) == len(free)

    # -- helpers ----------------------------------------------------------- #
    def _random_free_cell(self):
        taken = set(self.snake) | self.obstacles
        if self.food is not None:
            taken.add(self.food)
        if self.pickup is not None:
            taken.add(self.pickup.pos)
        free = [(x, y) for x in range(self.cols) for y in range(self.rows) if (x, y) not in taken]
        return self.rng.choice(free) if free else None
