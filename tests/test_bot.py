import random
import unittest

from snake_game import bot
from snake_game.engine import SnakeGame


def run_bot(mode, seed, max_steps, **kw):
    g = SnakeGame(mode=mode, rng=random.Random(seed), **kw)
    steps = 0
    while g.alive and steps < max_steps:
        bot.play_step(g, dt_ms=60)
        steps += 1
    return g, steps


class BotTests(unittest.TestCase):
    def test_bot_survives_and_scores_in_every_mode(self):
        for mode in ("classic", "wrap", "obstacles", "levels"):
            for seed in (1, 2, 3):
                g, steps = run_bot(mode, seed, 1500)
                self.assertGreater(g.score, 10, f"{mode} seed {seed}: score {g.score} after {steps} steps")
                self.assertGreater(steps, 150, f"{mode} seed {seed}: died after {steps} steps")

    def test_bot_never_picks_a_reversal(self):
        g = SnakeGame(rng=random.Random(5))
        for _ in range(300):
            if not g.alive:
                break
            d = bot.choose_direction(g)
            self.assertNotEqual(d, (-g.direction[0], -g.direction[1]))
            g.turns.clear()
            g.queue_turn(d)
            g.step(60)

    def test_bot_avoids_an_immediate_wall(self):
        g = SnakeGame(cols=10, rows=10, rng=random.Random(1), pickups=False)
        g.snake.clear()
        g.snake.extend([(9, 5), (8, 5), (7, 5)])  # heading right into the edge
        g.prev_snake = list(g.snake)
        g.food = (0, 5)
        bot.play_step(g)
        self.assertTrue(g.alive)


if __name__ == "__main__":
    unittest.main()
