"""A self-playing snake: BFS to the target, but only if the snake can still reach its own tail
afterwards (so it never boxes itself in). Falls back to chasing the tail, then to the move
with the most open space. Used for the menu background, the WATCH AI mode and as a test fuzzer."""

from collections import deque

from .config import opposite


def _bfs(game, start, goals, blocked):
    """Shortest path (list of cells, excluding start) to the nearest goal, or None."""
    goals = set(goals)
    if start in goals:
        return []
    parent = {start: None}
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        for nxt, _ in game.neighbors(cell):
            if nxt in parent or nxt in blocked:
                continue
            parent[nxt] = cell
            if nxt in goals:
                path = [nxt]
                while parent[path[-1]] != start:
                    path.append(parent[path[-1]])
                return path[::-1]
            queue.append(nxt)
    return None


def _flood_count(game, start, blocked, limit=10_000):
    seen = {start}
    stack = [start]
    while stack and len(seen) < limit:
        cell = stack.pop()
        for nxt, _ in game.neighbors(cell):
            if nxt not in seen and nxt not in blocked:
                seen.add(nxt)
                stack.append(nxt)
    return len(seen)


def _direction_between(a, b, game):
    for nxt, d in game.neighbors(a):
        if nxt == b:
            return d
    return None


def _body_blocked(game):
    """Cells that stay blocked next step: obstacles and the body (the tail moves away)."""
    return set(game.obstacles) | set(list(game.snake)[:-1])


def _simulate(game, path):
    """Snake cells after following `path`, growing if it ends on food."""
    snake = deque(game.snake)
    pending = game.pending_growth
    for cell in path:
        snake.appendleft(cell)
        if pending > 0:
            pending -= 1
        elif cell != game.food:
            snake.pop()
    return snake


def choose_direction(game):
    head = game.snake[0]
    tail = game.snake[-1]
    blocked = _body_blocked(game)

    targets = [game.food] if game.food else []
    if game.pickup is not None:
        targets.append(game.pickup.pos)

    # 1. Go for the nearest target, if we can still escape afterwards.
    path = _bfs(game, head, targets, blocked) if targets else None
    if path:
        after = _simulate(game, path)
        after_blocked = set(game.obstacles) | set(list(after)[:-1])
        if _bfs(game, after[0], [after[-1]], after_blocked) is not None:
            return _direction_between(head, path[0], game)

    # 2. Otherwise follow the tail: it is always a safe place to be heading.
    path = _bfs(game, head, [tail], blocked - {tail})
    if path:
        return _direction_between(head, path[0], game)

    # 3. Last resort: the legal move that leaves the most room.
    best, best_room = game.direction, -1
    for nxt, d in game.neighbors(head):
        if d == opposite(game.direction) or nxt in blocked:
            continue
        room = _flood_count(game, nxt, blocked | {head})
        if room > best_room:
            best, best_room = d, room
    return best


def play_step(game, dt_ms=0):
    """Let the bot choose a move, then advance the game one step. Returns step() events."""
    game.turns.clear()
    game.queue_turn(choose_direction(game))
    return game.step(dt_ms)
