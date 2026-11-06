"""Rules of the game: movement, collisions, food, pickups, modes. Run: python -m unittest discover -s tests -t ."""

import random
import unittest
from collections import deque

from snake_game import config
from snake_game.config import DOWN, LEFT, RIGHT, UP
from snake_game.engine import Pickup, SnakeGame, speed_for


def make_game(mode="classic", cols=10, rows=10, seed=1, **kw):
    return SnakeGame(cols=cols, rows=rows, mode=mode, rng=random.Random(seed), **kw)


class MovementTests(unittest.TestCase):
    def test_moves_one_cell_per_step(self):
        g = make_game()
        hx, hy = g.snake[0]
        g.step()
        self.assertEqual(g.snake[0], (hx + 1, hy))
        self.assertEqual(len(g.snake), 3)

    def test_cannot_reverse(self):
        g = make_game()
        g.queue_turn(LEFT)
        g.step()
        self.assertEqual(g.direction, RIGHT)
        self.assertTrue(g.alive)

    def test_quick_double_turn_is_buffered(self):
        g = make_game()
        g.queue_turn(UP)
        g.queue_turn(LEFT)
        g.step()
        g.step()
        self.assertEqual(g.direction, LEFT)
        self.assertTrue(g.alive)

    def test_reversal_check_uses_last_buffered_turn(self):
        g = make_game()
        g.queue_turn(UP)
        g.queue_turn(DOWN)
        self.assertEqual(list(g.turns), [UP])

    def test_prev_snake_tracks_last_step(self):
        g = make_game()
        before = list(g.snake)
        g.step()
        self.assertEqual(g.prev_snake, before)


class CollisionTests(unittest.TestCase):
    def test_wall_kills_in_classic(self):
        g = make_game()
        events = []
        while g.alive:
            events = g.step()
        self.assertEqual(events, ["dead"])

    def test_self_collision_kills(self):
        g = make_game()
        g.snake = deque([(5, 5), (5, 6), (4, 6), (4, 5), (4, 4), (5, 4)])
        g.direction = UP
        g.food = (0, 0)
        g.queue_turn(LEFT)
        self.assertEqual(g.step(), ["dead"])

    def test_chasing_own_tail_is_safe(self):
        g = make_game()
        g.snake = deque([(5, 5), (5, 6), (4, 6), (4, 5)])
        g.direction = UP
        g.food = (0, 0)
        g.queue_turn(LEFT)  # into the tail cell, which is vacated this step
        self.assertEqual(g.step(), [])
        self.assertTrue(g.alive)

    def test_tail_cell_is_deadly_while_growing(self):
        g = make_game()
        g.snake = deque([(5, 5), (5, 6), (4, 6), (4, 5)])
        g.direction = UP
        g.pending_growth = 1
        g.food = (0, 0)
        g.queue_turn(LEFT)
        self.assertEqual(g.step(), ["dead"])

    def test_dead_game_ignores_steps(self):
        g = make_game()
        g.alive = False
        self.assertEqual(g.step(), [])


class FoodTests(unittest.TestCase):
    def test_eating_grows_scores_and_respawns(self):
        g = make_game()
        hx, hy = g.snake[0]
        g.food = (hx + 1, hy)
        self.assertEqual(g.step(), ["eat"])
        self.assertEqual(g.score, 1)
        self.assertEqual(len(g.snake), 4)
        self.assertNotIn(g.food, g.snake)

    def test_food_never_spawns_on_snake_or_walls(self):
        g = make_game()
        g.obstacles = {(0, 0), (1, 1)}
        for _ in range(300):
            cell = g._random_free_cell()
            self.assertNotIn(cell, g.snake)
            self.assertNotIn(cell, g.obstacles)

    def test_filling_the_board_wins(self):
        g = SnakeGame(cols=3, rows=1, rng=random.Random(0), pickups=False)
        g.snake = deque([(1, 0), (0, 0)])
        g.food = (2, 0)
        events = g.step()
        self.assertIn("win", events)
        self.assertTrue(g.won)
        self.assertFalse(g.alive)

    def test_speed_ramps_and_caps(self):
        self.assertEqual(speed_for(10, 0), 10)
        self.assertEqual(speed_for(10, config.SPEED_STEP), 11)
        self.assertEqual(speed_for(10, 10_000), 10 + config.MAX_SPEED_BONUS)


class PickupTests(unittest.TestCase):
    def place(self, g, kind):
        hx, hy = g.snake[0]
        g.food = (0, 0)
        g.pickup = Pickup(kind, (hx + 1, hy), 3000)

    def test_bonus_gives_points_and_growth(self):
        g = make_game()
        self.place(g, config.BONUS)
        self.assertEqual(g.step(), ["pickup:bonus"])
        self.assertEqual(g.score, config.BONUS_POINTS)
        for _ in range(config.BONUS_POINTS):
            g.step()
        self.assertEqual(len(g.snake), 3 + config.BONUS_POINTS)

    def test_slow_slows_the_game_and_expires(self):
        g = make_game()
        self.place(g, config.SLOW)
        self.assertEqual(g.step(), ["pickup:slow"])
        self.assertEqual(g.speed_multiplier, config.SLOW_FACTOR)
        g.step(dt_ms=config.EFFECT_DURATION_MS[config.SLOW] + 1)
        self.assertEqual(g.speed_multiplier, 1.0)

    def test_double_doubles_food_points(self):
        g = make_game()
        self.place(g, config.DOUBLE)
        g.step()
        hx, hy = g.snake[0]
        g.food = (hx + 1, hy)
        g.step()
        self.assertEqual(g.score, 2)

    def test_ghost_passes_through_self_and_walls(self):
        g = make_game()
        self.place(g, config.GHOST)
        g.step()
        g.snake = deque([(5, 5), (5, 6), (4, 6), (4, 5), (4, 4), (5, 4)])
        g.direction = UP
        g.obstacles = {(4, 5)}
        g.queue_turn(LEFT)
        self.assertEqual(g.step(), [])
        self.assertTrue(g.alive)

    def test_ghost_still_dies_at_the_edge(self):
        g = make_game()
        g.effects[config.GHOST] = 99999
        events = []
        while g.alive:
            events = g.step()
        self.assertEqual(events, ["dead"])

    def test_ghost_waits_until_clear_of_walls(self):
        g = make_game()
        g.obstacles = {g.snake[0]}  # head is inside a wall
        g.effects[config.GHOST] = 10
        g.food = (0, 0)
        g.obstacles = {(g.snake[0][0] + 1, g.snake[0][1])}
        g.step(dt_ms=50)            # head enters the wall; ghost nominally expired
        self.assertIn(config.GHOST, g.effects)

    def test_pickup_expires_and_respawns_later(self):
        g = make_game()
        g.food = (0, 0)
        g.pickup = Pickup(config.SLOW, (9, 9), 100)
        g.step(dt_ms=150)
        self.assertIsNone(g.pickup)

    def test_pickups_can_be_disabled(self):
        g = make_game(pickups=False)
        g.pickup_cooldown = 0
        g.rng = random.Random(0)
        for _ in range(100):
            g.food = (0, 0)
            g.snake = deque([(5, 5), (4, 5), (3, 5)])
            g.direction = RIGHT
            g.step(dt_ms=1000)
            if not g.alive:
                break
        self.assertIsNone(g.pickup)


class WrapModeTests(unittest.TestCase):
    def test_wraps_instead_of_dying(self):
        g = make_game("wrap")
        for _ in range(25):
            self.assertEqual(g.step(), [])
        self.assertTrue(g.alive)
        self.assertTrue(all(0 <= x < g.cols and 0 <= y < g.rows for x, y in g.snake))

    def test_wrap_still_dies_on_self(self):
        g = make_game("wrap")
        g.snake = deque([(0, 0), (1, 0), (1, 1), (0, 1), (9, 1), (9, 0), (8, 0)])
        g.direction = LEFT   # head (0,0) -> wraps to (9,0), a body cell (the tail is (8,0))
        g.food = (5, 5)
        self.assertEqual(g.step(), ["dead"])


class ObstacleModeTests(unittest.TestCase):
    def test_walls_appear_every_n_foods(self):
        g = make_game("obstacles", cols=30, rows=20)
        self.assertEqual(g.obstacles, set())
        for _ in range(config.OBSTACLE_EVERY):
            hx, hy = g.snake[0]
            g.snake = deque([(hx, hy), (hx - 1, hy), (hx - 2, hy)])
            g.direction = RIGHT
            g.food = (hx + 1, hy)
            events = g.step()
        self.assertIn("obstacle", events)
        self.assertTrue(g.obstacles)

    def test_obstacles_never_disconnect_the_board(self):
        g = make_game("obstacles", cols=30, rows=20)
        for _ in range(40):
            g._add_obstacle()
            self.assertTrue(g._open_space_connected(g.obstacles))
        self.assertLessEqual(len(g.obstacles), config.MAX_OBSTACLE_CELLS)

    def test_obstacles_avoid_snake_food_and_head(self):
        g = make_game("obstacles", cols=30, rows=20)
        for _ in range(30):
            g._add_obstacle()
        self.assertFalse(g.obstacles & set(g.snake))
        self.assertNotIn(g.food, g.obstacles)
        hx, hy = g.snake[0]
        self.assertTrue(all(abs(x - hx) + abs(y - hy) > 5 for x, y in g.obstacles))

    def test_hitting_a_wall_kills(self):
        g = make_game("obstacles")
        hx, hy = g.snake[0]
        g.obstacles = {(hx + 1, hy)}
        g.food = (0, 0)
        self.assertEqual(g.step(), ["dead"])


class LevelsModeTests(unittest.TestCase):
    def test_clearing_a_level_loads_the_next_map(self):
        g = SnakeGame(mode="levels", rng=random.Random(2))
        self.assertEqual(g.level, 1)
        for _ in range(config.FOODS_PER_LEVEL):
            hx, hy = g.snake[0]
            g.food = (hx + 1, hy)
            g.snake = deque([(hx, hy), (hx - 1, hy), (hx - 2, hy)])
            g.direction = RIGHT
            events = g.step()
        self.assertIn("level", events)
        self.assertEqual(g.level, 2)
        self.assertTrue(g.obstacles)
        self.assertEqual(len(g.snake), 3)
        self.assertTrue(g.alive)
        self.assertEqual(g.score, config.FOODS_PER_LEVEL)

    def test_new_level_places_food_on_a_free_cell(self):
        g = SnakeGame(mode="levels", rng=random.Random(3))
        g._next_level()
        self.assertNotIn(g.food, g.obstacles)
        self.assertNotIn(g.food, g.snake)


class FuzzInvariantTests(unittest.TestCase):
    """Random play in every mode: the state must stay consistent no matter what."""

    def check(self, g):
        cells = list(g.snake)
        self.assertTrue(all(0 <= x < g.cols and 0 <= y < g.rows for x, y in cells))
        if config.GHOST not in g.effects:
            self.assertEqual(len(cells), len(set(cells)), "snake overlaps itself")
            self.assertFalse(set(cells) & g.obstacles, "snake inside a wall")
        if g.food is not None:
            self.assertNotIn(g.food, g.obstacles)
        if g.pickup is not None:
            self.assertNotIn(g.pickup.pos, g.obstacles)
            self.assertNotEqual(g.pickup.pos, g.food)

    def test_random_play_keeps_invariants(self):
        rng = random.Random(7)
        for mode in ("classic", "wrap", "obstacles", "levels"):
            for seed in range(8):
                kwargs = {} if mode == "levels" else {"cols": 12, "rows": 12}
                g = SnakeGame(mode=mode, rng=random.Random(seed), **kwargs)
                for _ in range(400):
                    if not g.alive:
                        break
                    if rng.random() < 0.3:
                        g.queue_turn(rng.choice(config.DIRECTIONS))
                    g.step(dt_ms=rng.choice((60, 100, 400, 1500)))
                    self.check(g)


if __name__ == "__main__":
    unittest.main()
