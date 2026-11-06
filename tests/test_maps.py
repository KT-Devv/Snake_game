import unittest

from snake_game.config import COLS, ROWS
from snake_game.maps import LEVELS, level_cells, level_name


class MapTests(unittest.TestCase):
    def test_every_map_is_in_bounds(self):
        for level in range(1, len(LEVELS) + 1):
            for x, y in level_cells(level):
                self.assertTrue(0 <= x < COLS and 0 <= y < ROWS, (level, x, y))

    def test_spawn_corridor_is_clear(self):
        for level in range(1, len(LEVELS) + 1):
            walls = level_cells(level)
            for x in range(12, 20):
                self.assertNotIn((x, ROWS // 2), walls, f"level {level} blocks the spawn corridor")

    def test_open_space_is_connected(self):
        for level in range(1, len(LEVELS) + 1):
            walls = level_cells(level)
            free = {(x, y) for x in range(COLS) for y in range(ROWS)} - walls
            start = (COLS // 2, ROWS // 2)
            seen, stack = {start}, [start]
            while stack:
                x, y = stack.pop()
                for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if n in free and n not in seen:
                        seen.add(n)
                        stack.append(n)
            self.assertEqual(seen, free, f"level {level} has unreachable cells")

    def test_levels_repeat_after_the_last(self):
        n = len(LEVELS)
        self.assertEqual(level_cells(n + 2), level_cells(2))
        self.assertEqual(level_name(n + 1), level_name(1))

    def test_first_level_is_open(self):
        self.assertEqual(level_cells(1), set())
