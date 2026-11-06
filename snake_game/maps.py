"""Hand-made maps for LEVELS mode.

The snake always spawns heading right from the board centre, so every map keeps the
corridor on row ROWS//2, columns 12-19, free. tests/test_maps.py checks that and that
each map leaves the open cells connected.
"""

from .config import COLS, ROWS


def _hline(x0, x1, y):
    return {(x, y) for x in range(x0, x1 + 1)}


def _vline(x, y0, y1):
    return {(x, y) for y in range(y0, y1 + 1)}


def _block(x, y, w, h):
    return {(x + i, y + j) for i in range(w) for j in range(h)}


def _open_field():
    return set()


def _pillars():
    cells = set()
    for x, y in ((5, 3), (23, 3), (5, 15), (23, 15), (14, 5), (14, 13)):
        cells |= _block(x, y, 2, 2)
    return cells


def _bars():
    return _hline(5, 24, 5) | _hline(5, 24, 14)


def _crossroads():
    cells = _vline(15, 1, 7) | _vline(15, 12, 18)
    cells |= _hline(2, 9, 10) | _hline(21, 28, 10)
    return cells


def _the_room():
    room = _hline(8, 21, 4) | _hline(8, 21, 15) | _vline(8, 4, 15) | _vline(21, 4, 15)
    room -= {(14, 4), (15, 4), (14, 15), (15, 15), (8, 9), (8, 10), (21, 9), (21, 10)}
    return room


def _zigzag():
    return _vline(7, 0, 13) | _vline(23, 6, 19) | _hline(12, 20, 3) | _hline(12, 20, 16)


LEVELS = (
    ("OPEN FIELD", _open_field),
    ("PILLARS", _pillars),
    ("THE BARS", _bars),
    ("CROSSROADS", _crossroads),
    ("THE ROOM", _the_room),
    ("ZIGZAG", _zigzag),
)


def level_name(level):
    return LEVELS[(level - 1) % len(LEVELS)][0]


def level_cells(level, cols=COLS, rows=ROWS):
    """Wall cells for a 1-based level number. Levels repeat after the last map."""
    builder = LEVELS[(level - 1) % len(LEVELS)][1]
    return {(x, y) for x, y in builder() if x < cols and y < rows}
