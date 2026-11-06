"""All drawing. Knows nothing about input or game flow, only how to paint a given state."""

import math

import pygame

from .config import (
    BLACK, BOARD_H, BOARD_W, BONUS, CELL, COLS, DIFFICULTIES, DOUBLE, EFFECT_DURATION_MS,
    GHOST, GOLD, HUD_H, MODES, PICKUP_LIFETIME_MS, PURPLE, RED, ROWS, SLOW, WHITE, WIN_H, WIN_W,
)

HEAD_COLOR = (110, 255, 150)
TAIL_COLOR = (20, 140, 95)
PALETTES = {
    "normal": (HEAD_COLOR, TAIL_COLOR),
    SLOW: ((130, 235, 255), (30, 110, 170)),
    DOUBLE: ((255, 230, 120), (190, 110, 30)),
    "dead": ((210, 100, 100), (90, 40, 55)),
}
PICKUP_STYLE = {  # ring/fill colour, accent colour, glyph
    BONUS: (PURPLE, GOLD, ""),
    SLOW: ((90, 200, 255), WHITE, "S"),
    GHOST: ((190, 200, 255), (110, 120, 220), "G"),
    DOUBLE: ((255, 160, 50), WHITE, "x2"),
}
EFFECT_LABEL = {SLOW: "SLOW", GHOST: "GHOST", DOUBLE: "x2"}
EFFECT_COLOR = {SLOW: (90, 200, 255), GHOST: (190, 200, 255), DOUBLE: (255, 170, 60)}


def lerp_color(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def snake_points(game, alpha):
    """Float cell coordinates per segment, interpolated between the last two steps.

    Segment i moved from prev[i] to cur[i] (the whole body slides one cell along its path).
    A jump of more than a cell means a wrap-around or respawn, which just snaps.
    """
    cur, prev = list(game.snake), game.prev_snake
    alpha = max(0.0, min(1.0, alpha))
    points = []
    for i, (cx, cy) in enumerate(cur):
        px, py = prev[min(i, len(prev) - 1)]
        if abs(cx - px) > 1 or abs(cy - py) > 1:
            points.append((float(cx), float(cy)))
        else:
            points.append((px + (cx - px) * alpha, py + (cy - py) * alpha))
    return points


class Renderer:
    def __init__(self, screen, asset_dir):
        self.screen = screen
        font_path = str(asset_dir / "PressStart2P-Regular.ttf")
        self.font_big = self._font(font_path, 28)
        self.font_med = self._font(font_path, 14)
        self.font_small = self._font(font_path, 10)
        self.font_tiny = self._font(font_path, 8)

        self.base = pygame.Surface((WIN_W, WIN_H))
        self.base.fill((60, 40, 90))
        bg = self._image(asset_dir / "background.jpg", (WIN_W, WIN_H))
        if bg:
            self.base.blit(bg, (0, 0))
        self.intro = self._image(asset_dir / "intro_image.jpg", (BOARD_W, BOARD_H))
        if self.intro:
            self.intro.set_alpha(45)
        self.assets_ok = bool(bg and self.intro)

        self.board_layer = pygame.Surface((BOARD_W, BOARD_H), pygame.SRCALPHA)
        for cx in range(COLS):
            for cy in range(ROWS):
                alpha = 150 if (cx + cy) % 2 == 0 else 125
                pygame.draw.rect(self.board_layer, (20, 14, 40, alpha), (cx * CELL, cy * CELL, CELL, CELL))
        self.hud_layer = pygame.Surface((WIN_W, HUD_H), pygame.SRCALPHA)
        self.hud_layer.fill((15, 10, 30, 215))
        self.dim_board = pygame.Surface((BOARD_W, BOARD_H), pygame.SRCALPHA)
        self.dim_board.fill((10, 6, 24, 170))
        self.dim_window = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        self.dim_window.fill((10, 6, 24, 140))
        self.snake_layer = pygame.Surface((BOARD_W, BOARD_H), pygame.SRCALPHA)

    # -- loading ----------------------------------------------------------- #
    @staticmethod
    def _font(path, size):
        try:
            return pygame.font.Font(path, size)
        except (pygame.error, FileNotFoundError, OSError):
            return pygame.font.Font(None, int(size * 1.7))

    @staticmethod
    def _image(path, size):
        try:
            return pygame.transform.smoothscale(pygame.image.load(str(path)).convert(), size)
        except (pygame.error, FileNotFoundError):
            return None

    # -- text -------------------------------------------------------------- #
    def text(self, msg, font, color, *, center=None, topleft=None, topright=None, midleft=None, shadow=True):
        img = font.render(msg, True, color)
        rect = img.get_rect()
        if center:
            rect.center = center
        elif topleft:
            rect.topleft = topleft
        elif topright:
            rect.topright = topright
        elif midleft:
            rect.midleft = midleft
        if shadow:
            self.screen.blit(font.render(msg, True, BLACK), rect.move(2, 2))
        self.screen.blit(img, rect)
        return rect

    def background(self):
        self.screen.blit(self.base, (0, 0))

    # -- the board --------------------------------------------------------- #
    def board(self, game, alpha, t, accent, particles=(), offset=(0, 0), dead=False):
        s = self.screen
        ox, oy = offset[0], HUD_H + offset[1]
        s.blit(self.board_layer, (ox, oy))

        for x, y in game.obstacles:
            rect = pygame.Rect(ox + x * CELL + 1, oy + y * CELL + 1, CELL - 2, CELL - 2)
            pygame.draw.rect(s, (98, 86, 150), rect, border_radius=3)
            pygame.draw.rect(s, (140, 128, 196), (rect.x + 2, rect.y + 2, rect.w - 4, 3), border_radius=2)
            pygame.draw.rect(s, (55, 46, 96), rect, 1, border_radius=3)

        if game.food:
            cx, cy = self._center(game.food, ox, oy)
            r = int(CELL * 0.38 * (1 + 0.08 * math.sin(t * 6)))
            pygame.draw.circle(s, RED, (cx, cy), r + 1)
            pygame.draw.circle(s, (255, 140, 150), (cx - r // 3, cy - r // 3), max(2, r // 3))

        if game.pickup:
            self._draw_pickup(game.pickup, ox, oy, t)

        self._draw_snake(game, alpha, ox, oy, dead)

        for p in particles:
            a = max(0.0, p.life / p.max_life)
            size = max(1, int(4 * a))
            pygame.draw.rect(s, lerp_color(BLACK, p.color, 0.4 + 0.6 * a),
                             (ox + int(p.x) - size // 2, oy + int(p.y) - size // 2, size, size))

        pygame.draw.rect(s, accent, (ox, oy, BOARD_W, BOARD_H), 2)

    @staticmethod
    def _center(cell, ox, oy):
        return ox + cell[0] * CELL + CELL // 2, oy + cell[1] * CELL + CELL // 2

    def _draw_pickup(self, pickup, ox, oy, t):
        s = self.screen
        color, accent, glyph = PICKUP_STYLE[pickup.kind]
        frac = max(0.0, pickup.left_ms / PICKUP_LIFETIME_MS)
        if frac <= 0.3 and int(t * 8) % 2:
            return  # blink when about to vanish
        cx, cy = self._center(pickup.pos, ox, oy)
        r = int(CELL * 0.42 + 1.5 * math.sin(t * 9))
        pygame.draw.circle(s, color, (cx, cy), r)
        if glyph:
            img = self.font_tiny.render(glyph, True, accent if pickup.kind == GHOST else BLACK)
            s.blit(img, img.get_rect(center=(cx, cy)))
        else:
            pygame.draw.circle(s, accent, (cx, cy), max(2, r // 3))
        ring = pygame.Rect(0, 0, CELL + 6, CELL + 6)
        ring.center = (cx, cy)
        pygame.draw.arc(s, GOLD, ring, math.pi / 2, math.pi / 2 + math.tau * frac, 2)

    def _draw_snake(self, game, alpha, ox, oy, dead):
        layer = self.snake_layer
        layer.fill((0, 0, 0, 0))
        points = snake_points(game, 1.0 if dead else alpha)
        n = len(points)
        if dead:
            palette = PALETTES["dead"]
        elif DOUBLE in game.effects:
            palette = PALETTES[DOUBLE]
        elif SLOW in game.effects:
            palette = PALETTES[SLOW]
        else:
            palette = PALETTES["normal"]

        def px(p):
            return (p[0] + 0.5) * CELL, (p[1] + 0.5) * CELL

        for i in range(n - 1, -1, -1):
            frac = i / max(1, n - 1)
            color = lerp_color(palette[0], palette[1], frac)
            radius = 9 - 3 * frac
            x, y = px(points[i])
            if i > 0:  # join to the segment ahead (skip across a wrap-around)
                x2, y2 = px(points[i - 1])
                if abs(x2 - x) < CELL * 1.5 and abs(y2 - y) < CELL * 1.5:
                    pygame.draw.line(layer, color, (x, y), (x2, y2), int(radius * 2))
            pygame.draw.circle(layer, color, (x, y), radius)

        hx, hy = px(points[0])
        dx, dy = game.direction
        for side in (-1, 1):
            ex = hx + dx * 3 + (-dy) * 4 * side
            ey = hy + dy * 3 + dx * 4 * side
            pygame.draw.circle(layer, WHITE, (ex, ey), 3)
            pygame.draw.circle(layer, BLACK, (ex + dx, ey + dy), 1)

        layer.set_alpha(150 if GHOST in game.effects and not dead else 255)
        self.screen.blit(layer, (ox, oy))

    # -- HUD --------------------------------------------------------------- #
    def hud(self, game, label, time_ms, best, accent):
        self.screen.blit(self.hud_layer, (0, 0))
        self.text(f"SCORE {game.score}", self.font_small, WHITE, topleft=(14, 9))
        secs = time_ms // 1000
        self.text(f"{secs // 60}:{secs % 60:02d}", self.font_small, accent, center=(WIN_W // 2, 14))
        self.text(f"BEST {max(best, game.score)}", self.font_small, GOLD, topright=(WIN_W - 14, 9))

        self.text(label, self.font_tiny, (190, 180, 220), midleft=(14, 35), shadow=False)
        if game.mode == "levels":
            self.text(f"LEVEL {game.level}", self.font_tiny, (190, 180, 220), center=(WIN_W // 2, 35),
                      shadow=False)
        x = WIN_W - 14
        for kind, left in game.effects.items():
            w = 64
            x -= w
            frac = max(0.0, min(1.0, left / EFFECT_DURATION_MS[kind]))
            pygame.draw.rect(self.screen, (40, 32, 70), (x, 29, w - 6, 12), border_radius=3)
            pygame.draw.rect(self.screen, EFFECT_COLOR[kind], (x, 29, int((w - 6) * frac), 12), border_radius=3)
            self.text(EFFECT_LABEL[kind], self.font_tiny, WHITE, center=(x + (w - 6) // 2, 35))

    # -- overlays ---------------------------------------------------------- #
    def banner(self, title, subtitle, t=0.0):
        """Shown before a run or level starts."""
        cy = HUD_H + 120
        self.text(title, self.font_big, WHITE, center=(WIN_W // 2, cy))
        self.text(subtitle, self.font_small, (225, 220, 245), center=(WIN_W // 2, cy + 40))
        if int(t * 2) % 2 == 0:
            self.text("PRESS A DIRECTION TO START", self.font_tiny, GOLD, center=(WIN_W // 2, cy + 72))

    def overlay(self, title, lines, color=WHITE, backdrop=False):
        self.screen.blit(self.dim_board, (0, HUD_H))
        if backdrop and self.intro:
            self.screen.blit(self.intro, (0, HUD_H))
        cy = HUD_H + BOARD_H // 2
        top = cy - 30 - 12 * max(0, len(lines) - 3)
        self.text(title, self.font_big, color, center=(WIN_W // 2, top))
        for i, (line, line_color) in enumerate(lines):
            self.text(line, self.font_small, line_color, center=(WIN_W // 2, top + 50 + i * 24))

    def toast(self, msg, y):
        img = self.font_small.render(msg, True, WHITE)
        rect = img.get_rect(center=(WIN_W // 2, y))
        pad = pygame.Rect(rect).inflate(24, 14)
        pygame.draw.rect(self.screen, (15, 10, 30), pad, border_radius=8)
        pygame.draw.rect(self.screen, GOLD, pad, 2, border_radius=8)
        self.screen.blit(img, rect)

    # -- menus ------------------------------------------------------------- #
    def menu(self, rows, index, t, blurb, hint):
        """rows: [(label, value_text or None, bar 0..1 or None, accent colour or None)].
        Returns one hit rectangle per row."""
        s = self.screen
        s.blit(self.dim_window, (0, 0))
        panel = pygame.Rect(0, 0, 480, 404)
        panel.center = (WIN_W // 2, WIN_H // 2)
        bg = pygame.Surface(panel.size, pygame.SRCALPHA)
        pygame.draw.rect(bg, (15, 10, 30, 225), bg.get_rect(), border_radius=14)
        s.blit(bg, panel)

        bob = int(math.sin(t * 3) * 3)
        self.text("SNAKE", self.font_big, HEAD_COLOR, center=(WIN_W // 2, panel.top + 44 + bob))

        rects = []
        top = panel.top + 96
        for i, (label, value, bar, color) in enumerate(rows):
            y = top + i * 31
            selected = i == index
            row = pygame.Rect(panel.left + 22, y - 14, panel.width - 44, 28)
            rects.append(row)
            accent = color or (255, 255, 255)
            if selected:
                pygame.draw.rect(s, accent, row, 2, border_radius=8)
            text_color = accent if selected else (190, 185, 210)
            if value is None and bar is None:
                self.text(label, self.font_med, text_color, center=row.center, shadow=selected)
                continue
            self.text(label, self.font_small, text_color, midleft=(row.left + 14, y), shadow=selected)
            if bar is not None:
                self._draw_bar(row.right - 150, y - 6, 130, 12, bar, accent if selected else (150, 145, 175))
            else:
                shown = f"< {value} >" if selected else value
                self.text(shown, self.font_small, text_color, midleft=(row.right - 190, y), shadow=selected)

        self.text(blurb, self.font_tiny, (215, 205, 240), center=(WIN_W // 2, panel.bottom - 44))
        self.text(hint, self.font_tiny, (150, 142, 180), center=(WIN_W // 2, panel.bottom - 22), shadow=False)
        return rects

    def _draw_bar(self, x, y, w, h, frac, color):
        pygame.draw.rect(self.screen, (40, 32, 70), (x, y, w, h), border_radius=4)
        if frac > 0:
            pygame.draw.rect(self.screen, color, (x, y, max(4, int(w * frac)), h), border_radius=4)

    def scores_table(self, best_of, t):
        s = self.screen
        s.blit(self.dim_window, (0, 0))
        panel = pygame.Rect(0, 0, 520, 340)
        panel.center = (WIN_W // 2, WIN_H // 2)
        bg = pygame.Surface(panel.size, pygame.SRCALPHA)
        pygame.draw.rect(bg, (15, 10, 30, 230), bg.get_rect(), border_radius=14)
        s.blit(bg, panel)

        self.text("HIGH SCORES", self.font_med, GOLD, center=(WIN_W // 2, panel.top + 36))
        col_x = [panel.left + 150 + i * 120 for i in range(len(DIFFICULTIES))]
        for x, diff in zip(col_x, DIFFICULTIES):
            self.text(diff.label, self.font_small, diff.color, center=(x, panel.top + 84))
        for r, mode in enumerate(MODES):
            y = panel.top + 130 + r * 44
            self.text(mode.label, self.font_small, (225, 220, 245), midleft=(panel.left + 24, y))
            for x, diff in zip(col_x, DIFFICULTIES):
                value = best_of(mode.key, diff.key)
                self.text(str(value) if value else "-", self.font_small,
                          WHITE if value else (110, 105, 135), center=(x, y))
        self.text("ESC  BACK", self.font_tiny, (150, 142, 180), center=(WIN_W // 2, panel.bottom - 24),
                  shadow=False)
