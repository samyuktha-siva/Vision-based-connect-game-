"""Everything that is drawn with Pygame. Game rules live in game_logic.py."""

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

import pygame

from game import settings as S
from game.board import Cell, LevelData
from game.game_logic import GameState, Status


@dataclass
class Button:
    id: str
    rect: pygame.Rect
    label: str
    enabled: bool = True
    primary: bool = False


def format_time(seconds: float) -> str:
    seconds = max(0, int(math.ceil(seconds)))
    return f"{seconds // 60}:{seconds % 60:02d}"


def draw_shape(surface, shape, center, r, color):
    """The extra cue inside each dot: circle, square, triangle, diamond, plus, star."""
    x, y = center
    if shape == "circle":
        pygame.draw.circle(surface, color, center, r)
    elif shape == "square":
        pygame.draw.rect(surface, color, (x - r, y - r, 2 * r, 2 * r), border_radius=3)
    elif shape == "triangle":
        pygame.draw.polygon(surface, color, [(x, y - r), (x - r, y + r * 0.8), (x + r, y + r * 0.8)])
    elif shape == "diamond":
        pygame.draw.polygon(surface, color, [(x, y - r * 1.2), (x + r, y), (x, y + r * 1.2), (x - r, y)])
    elif shape == "plus":
        t = max(2, r // 2)
        pygame.draw.rect(surface, color, (x - r, y - t // 2, 2 * r, t))
        pygame.draw.rect(surface, color, (x - t // 2, y - r, t, 2 * r))
    elif shape == "star":
        pts = []
        for i in range(10):
            rad = r * 1.2 if i % 2 == 0 else r * 0.5
            ang = -math.pi / 2 + i * math.pi / 5
            pts.append((x + rad * math.cos(ang), y + rad * math.sin(ang)))
        pygame.draw.polygon(surface, color, pts)


class BoardView:
    """Converts between grid cells and window pixels."""

    def __init__(self, level: LevelData, area: pygame.Rect):
        self.level = level
        self.cell = min(area.width // level.width, area.height // level.height)
        w, h = self.cell * level.width, self.cell * level.height
        self.rect = pygame.Rect(0, 0, w, h)
        self.rect.center = area.center

    def cell_rect(self, cell: Cell) -> pygame.Rect:
        return pygame.Rect(self.rect.left + cell[0] * self.cell,
                           self.rect.top + cell[1] * self.cell, self.cell, self.cell)

    def center(self, cell: Cell) -> Tuple[int, int]:
        return self.cell_rect(cell).center

    def cell_at(self, pos) -> Optional[Cell]:
        if pos is None or not self.rect.collidepoint(pos):
            return None
        return ((pos[0] - self.rect.left) // self.cell, (pos[1] - self.rect.top) // self.cell)


class UI:
    BOARD_AREA = pygame.Rect(40, 100, 600, 600)
    PANEL = pygame.Rect(670, 30, 400, 660)

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self._fonts = {}
        self.w, self.h = screen.get_size()

    # ------------------------------------------------------------ helpers
    def font(self, size: int, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        if key not in self._fonts:
            self._fonts[key] = pygame.font.SysFont("segoeui,arial,helvetica,dejavusans",
                                                   size, bold=bold)
        return self._fonts[key]

    def text(self, s, size, color, pos, anchor="topleft", bold=False):
        img = self.font(size, bold).render(s, True, color)
        rect = img.get_rect(**{anchor: pos})
        self.screen.blit(img, rect)
        return rect

    def wrapped(self, s, size, color, rect, bold=False, line_gap=4, center=False):
        font = self.font(size, bold)
        lines, line = [], ""
        for word in s.split():
            test = (line + " " + word).strip()
            if font.size(test)[0] <= rect.width:
                line = test
            else:
                lines.append(line)
                line = word
        lines.append(line)
        y = rect.top
        for ln in lines:
            img = font.render(ln, True, color)
            x = rect.centerx - img.get_width() // 2 if center else rect.left
            self.screen.blit(img, (x, y))
            y += img.get_height() + line_gap
        return y

    def panel(self, rect, color=S.PANEL, radius=18):
        pygame.draw.rect(self.screen, color, rect, border_radius=radius)

    def button(self, b: Button, hover: bool):
        if not b.enabled:
            fill, fg = S.PANEL, S.DISABLED
        elif b.primary:
            fill, fg = ((150, 215, 255) if hover else S.ACCENT), (20, 26, 46)
        else:
            fill, fg = (S.PANEL_LIGHT if not hover else (72, 82, 122)), S.TEXT
        pygame.draw.rect(self.screen, fill, b.rect, border_radius=14)
        border = S.TEXT if (hover and b.enabled) else S.PANEL_LIGHT
        pygame.draw.rect(self.screen, border, b.rect, 2, border_radius=14)
        self.text(b.label, 22, fg, b.rect.center, "center", bold=True)

    def pairs_icons(self, game: GameState, x, y):
        for i, color in enumerate(game.level.dots):
            c = (x + i * 40 + 16, y + 16)
            done = color in game.completed
            rgb = S.COLOR_RGB[color]
            pygame.draw.circle(self.screen, rgb if done else S.PANEL_LIGHT, c, 16)
            pygame.draw.circle(self.screen, rgb, c, 16, 2)
            draw_shape(self.screen, S.COLOR_SHAPES[color], c, 6,
                       (20, 26, 46) if done else rgb)

    def cursor(self, pos, pinching, color=None):
        """The hand cursor: an open ring, filled while pinching."""
        if pos is None:
            return
        pos = (int(pos[0]), int(pos[1]))
        if pinching:
            pygame.draw.circle(self.screen, color or S.TEXT, pos, 14)
            pygame.draw.circle(self.screen, S.TEXT, pos, 14, 3)
        else:
            pygame.draw.circle(self.screen, S.TEXT, pos, 18, 3)
            pygame.draw.circle(self.screen, S.TEXT, pos, 3)

    # ---------------------------------------------------------- background
    def background(self):
        self.screen.fill(S.BACKGROUND)

    # ----------------------------------------------------------- game board
    def draw_board(self, game: GameState, view: BoardView, hover_cell: Optional[Cell]):
        level = game.level
        pygame.draw.rect(self.screen, S.PANEL, view.rect.inflate(16, 16), border_radius=18)
        for y in range(level.height):
            for x in range(level.width):
                r = view.cell_rect((x, y)).inflate(-4, -4)
                pygame.draw.rect(self.screen, S.CELL, r, border_radius=8)
                if (x, y) in level.obstacles:
                    self._obstacle(r)
        if hover_cell is not None and hover_cell not in level.obstacles:
            pygame.draw.rect(self.screen, S.TEXT_DIM,
                             view.cell_rect(hover_cell).inflate(-4, -4), 2, border_radius=8)
        width = max(8, int(view.cell * 0.3))
        for color, path in game.paths.items():
            rgb = S.COLOR_RGB[color]
            pts = [view.center(c) for c in path]
            if len(pts) > 1:
                pygame.draw.lines(self.screen, rgb, False, pts, width)
            for p in pts:
                pygame.draw.circle(self.screen, rgb, p, width // 2)
        for color, (a, b) in level.dots.items():
            for cell in (a, b):
                self._dot(color, view.center(cell), view.cell, color in game.completed)

    def _obstacle(self, r):
        pygame.draw.rect(self.screen, S.OBSTACLE, r, border_radius=8)
        clip = self.screen.get_clip()
        self.screen.set_clip(r)
        for off in range(-r.height, r.width, 12):
            pygame.draw.line(self.screen, S.OBSTACLE_DARK, (r.left + off, r.bottom),
                             (r.left + off + r.height, r.top), 3)
        self.screen.set_clip(clip)
        pygame.draw.rect(self.screen, S.OBSTACLE_DARK, r, 3, border_radius=8)

    def _dot(self, color, center, cell, done):
        rgb = S.COLOR_RGB[color]
        radius = int(cell * 0.36)
        pygame.draw.circle(self.screen, S.TEXT, center, radius + 3)
        pygame.draw.circle(self.screen, rgb, center, radius)
        draw_shape(self.screen, S.COLOR_SHAPES[color], center, int(radius * 0.45), (20, 26, 46))
        if done:
            pygame.draw.circle(self.screen, S.GOOD, center, radius + 6, 3)

    # ------------------------------------------------------------ game HUD
    def game_buttons(self, game: GameState, has_next: bool) -> List[Button]:
        x, w, h, gap = 880, 170, 46, 10
        top = 456
        paused = game.status == Status.PAUSED
        return [
            Button("pause", pygame.Rect(x, top, w, h), "Resume" if paused else "Pause",
                   game.status in (Status.PLAYING, Status.READY, Status.PAUSED)),
            Button("restart", pygame.Rect(x, top + (h + gap), w, h), "Restart"),
            Button("next", pygame.Rect(x, top + 2 * (h + gap), w, h), "Next Level",
                   game.status == Status.WON and has_next, primary=game.status == Status.WON),
            Button("exit", pygame.Rect(x, top + 3 * (h + gap), w, h), "Exit"),
        ]

    def draw_hud(self, game: GameState, total_score: int, buttons, hover_id,
                 keyboard_mode: bool, preview_surface, hand_seen: bool, show_preview: bool):
        self.text("Gesture Connect", 34, S.TEXT, (40, 30), bold=True)
        self.text("Connect each pair of matching dots", 20, S.TEXT_DIM, (40, 70))
        self.panel(self.PANEL)
        x = self.PANEL.left + 24
        self.text(f"Level {game.level.number} of 10", 30, S.ACCENT, (x, 50), bold=True)
        low = game.time_left <= 15 and game.status == Status.PLAYING
        rows = [("Time", format_time(game.time_left), S.SOFT_WARN if low else S.TEXT),
                ("Score", str(total_score + game.score), S.TEXT),
                ("Pairs", f"{game.pairs_done} of {game.pairs_total}", S.TEXT),
                ("Status", game.status.value, S.GOOD if game.status == Status.WON else S.TEXT)]
        for i, (label, value, color) in enumerate(rows):
            y = 100 + i * 42
            self.text(label, 22, S.TEXT_DIM, (x, y))
            self.text(value, 28, color, (self.PANEL.right - 24, y - 4), "topright", bold=True)
        self.pairs_icons(game, x, 270)
        fb_color = S.SOFT_WARN if game.feedback.kind == "invalid" else S.TEXT
        self.wrapped(game.feedback.message, 21, fb_color,
                     pygame.Rect(x, 322, self.PANEL.width - 48, 80))
        if keyboard_mode:
            self.wrapped("KEYBOARD TEST MODE (not webcam play): arrows move, Space pinches.",
                         16, S.SOFT_WARN, pygame.Rect(x, 392, self.PANEL.width - 48, 50))
        else:
            self.wrapped("Pinch thumb and finger over a dot, move to its partner, then let go.",
                         16, S.TEXT_DIM, pygame.Rect(x, 392, self.PANEL.width - 48, 50))
        if show_preview and not keyboard_mode:
            r = pygame.Rect(x, 478, 160, 120)
            if preview_surface is not None:
                self.screen.blit(preview_surface, r)
            else:
                pygame.draw.rect(self.screen, S.CELL, r)
            pygame.draw.rect(self.screen, S.PANEL_LIGHT, r, 2)
            self.text("Hand seen" if hand_seen else "Show your hand", 16,
                      S.GOOD if hand_seen else S.TEXT_DIM, (r.centerx, r.bottom + 6), "midtop")
        for b in buttons:
            self.button(b, hover_id == b.id)

    # ------------------------------------------------------------ overlays
    def overlay(self, title, message, buttons, hover_id, still=None, effects=None):
        shade = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        shade.fill((10, 12, 24, 190))
        self.screen.blit(shade, (0, 0))
        box = pygame.Rect(0, 0, 640, 380)
        box.center = (self.w // 2, self.h // 2)
        self.panel(box, S.PANEL, 24)
        pygame.draw.rect(self.screen, S.ACCENT, box, 3, border_radius=24)
        if still is not None:
            still(self.screen, pygame.Rect(box.left, box.top - 10, box.width, 80))
        self.text(title, 40, S.TEXT, (box.centerx, box.top + 100), "center", bold=True)
        self.wrapped(message, 24, S.TEXT, pygame.Rect(box.left + 40, box.top + 150,
                                                      box.width - 80, 100), center=True)
        for b in buttons:
            self.button(b, hover_id == b.id)

    def overlay_buttons(self, specs) -> List[Button]:
        """specs: list of (id, label, enabled, primary). Placed in one centred row."""
        h, gap = 52, 14
        w = min(170, (600 - (len(specs) - 1) * gap) // len(specs))
        total = len(specs) * w + (len(specs) - 1) * gap
        left = self.w // 2 - total // 2
        top = self.h // 2 + 190 - 80
        return [Button(i, pygame.Rect(left + n * (w + gap), top, w, h), label, en, pr)
                for n, (i, label, en, pr) in enumerate(specs)]

    # ---------------------------------------------------------------- menu
    def menu_buttons(self, settings, levels) -> List[Button]:
        cx = self.w // 2
        out = [Button("start", pygame.Rect(cx - 150, 258, 300, 60), "Start Game", primary=True)]
        for n in range(1, levels.total + 1):
            col = (n - 1) % 5
            row = (n - 1) // 5
            rect = pygame.Rect(cx - 176 + col * 72, 355 + row * 62, 64, 52)
            unlocked = levels.is_unlocked(n)
            out.append(Button(f"level_{n}", rect, str(n) if unlocked else f"{n}*", unlocked))
        y = 495
        out.append(Button("difficulty", pygame.Rect(cx - 310, y, 300, 46),
                          f"Time: {settings.difficulty_name}"))
        out.append(Button("animations", pygame.Rect(cx + 10, y, 300, 46),
                          f"Animations: {'On' if settings.animations else 'Off'}"))
        out.append(Button("preview", pygame.Rect(cx - 310, y + 56, 300, 46),
                          f"Camera preview: {'On' if settings.show_preview else 'Off'}"))
        out.append(Button("keyboard", pygame.Rect(cx + 10, y + 56, 300, 46),
                          f"Keyboard test mode: {'On' if settings.keyboard_mode else 'Off'}"))
        out.append(Button("exit", pygame.Rect(cx - 150, y + 120, 300, 46), "Exit"))
        return out

    def draw_menu(self, buttons, hover_id, camera_status, keyboard_mode, camera_message):
        self.background()
        cx = self.w // 2
        self.text("Gesture Connect", 64, S.TEXT, (cx, 70), "midtop", bold=True)
        self.text("Join the matching dots using your hand!", 28, S.TEXT_DIM, (cx, 150), "midtop")
        # decorative dots
        for i, color in enumerate(S.COLOR_NAMES):
            self._dot(color, (cx - 200 + i * 80, 208), 80, False)
        self.text("Levels  (* = finish the one before to unlock)", 18, S.TEXT_DIM,
                  (cx, 332), "midtop")
        for b in buttons:
            self.button(b, hover_id == b.id)
        if keyboard_mode:
            msg, col = "Keyboard test mode is ON. This is not webcam play.", S.SOFT_WARN
        elif camera_status == "running":
            msg, col = "Camera ready. Pinch over a button to press it.", S.GOOD
        elif camera_status == "error":
            msg, col = camera_message, S.SOFT_WARN
        else:
            msg, col = "Starting the camera...", S.TEXT_DIM
        self.text(msg[:120], 18, col, (cx, self.h - 34), "midtop")

    def draw_camera_screen(self, status, message, buttons, hover_id):
        self.background()
        cx = self.w // 2
        if status == "error":
            self.text("We can't see the camera yet", 44, S.TEXT, (cx, 150), "midtop", bold=True)
            self.wrapped(message, 24, S.SOFT_WARN, pygame.Rect(cx - 380, 230, 760, 120),
                         center=True)
        else:
            self.text("Starting the camera...", 44, S.TEXT, (cx, 200), "midtop", bold=True)
            self.text("This can take a few seconds.", 24, S.TEXT_DIM, (cx, 270), "midtop")
        for b in buttons:
            self.button(b, hover_id == b.id)

    def camera_buttons(self) -> List[Button]:
        cx = self.w // 2
        return [Button("retry", pygame.Rect(cx - 160, 400, 320, 56), "Try camera again", primary=True),
                Button("use_keyboard", pygame.Rect(cx - 160, 470, 320, 52),
                       "Use keyboard test mode"),
                Button("menu", pygame.Rect(cx - 160, 540, 320, 52), "Back to menu")]

    def draw_final(self, buttons, hover_id, effects, animations):
        self.background()
        cx = self.w // 2
        self.text("Congratulations!", 64, S.TEXT, (cx, 110), "midtop", bold=True)
        self.wrapped("You finished all ten levels! Thank you for playing. "
                     "You should be very proud of yourself!", 28, S.TEXT,
                     pygame.Rect(cx - 360, 210, 720, 120), center=True)
        if not animations:
            effects.draw_still_celebration(self.screen, pygame.Rect(0, 330, self.w, 120))
        for b in buttons:
            self.button(b, hover_id == b.id)
