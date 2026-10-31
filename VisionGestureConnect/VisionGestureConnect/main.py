"""Vision-Based Gesture Connect Game: start the game with  python main.py"""

import os
import sys
import time
from typing import List, Optional

import pygame

from game import settings as S
from game.effects import Effects
from game.game_logic import GameState, Status
from game.level_manager import LevelManager
from game.ui import UI, BoardView, Button
from vision.gesture_detector import GestureDetector
from vision.hand_tracker import HandTracker

PROGRESS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "progress.json")


class App:
    def __init__(self, tracker=None):
        pygame.init()
        pygame.display.set_caption(S.APP_TITLE)
        self.screen = pygame.display.set_mode(S.WINDOW_SIZE)
        self.clock = pygame.time.Clock()
        self.settings = S.Settings()
        self.levels = LevelManager(PROGRESS_FILE)
        self.ui = UI(self.screen)
        self.effects = Effects()
        self.tracker = tracker if tracker is not None else HandTracker(S.CAMERA_INDEX, S.CAMERA_SIZE)
        self.detector = self._new_detector()
        self.running = True
        self.screen_state = "menu"          # menu, camera, game, final
        self.camera_return = "start"        # what to do once the camera works
        self.game: Optional[GameState] = None
        self.view: Optional[BoardView] = None
        self.score_before = 0               # score from earlier levels
        self.pointer = None                 # cursor position in window pixels
        self.pinching = False
        self.pinch_mode: Optional[str] = None   # "button", "draw" or None
        self.hand_seen = False
        self.kb_cell = (0, 0)
        self.kb_pinch = False
        self._kb_started = False
        self._kb_ended = False
        self._fb_id = 0
        self.tracker.start()                # opens the camera in the background

    # ------------------------------------------------------------ set up
    def _new_detector(self) -> GestureDetector:
        s = self.settings
        return GestureDetector(s.pinch_start_ratio, s.pinch_release_ratio, s.smoothing,
                               S.LOST_GRACE_SECONDS, S.ACTIVE_MARGIN)

    def begin(self, number: int) -> None:
        """Start the game at a level (from the menu). Needs the camera or keyboard mode."""
        self.levels.select(number)
        self.score_before = 0
        if self.settings.keyboard_mode or self.tracker.status == "running":
            self.start_level()
        else:
            self.camera_return = "start"
            self.screen_state = "camera"
            if self.tracker.status == "stopped":
                self.tracker.start()

    def start_level(self) -> None:
        level = self.levels.level()
        limit = level.time_limit * self.settings.time_multiplier
        self.game = GameState(level, limit)
        self.view = BoardView(level, UI.BOARD_AREA)
        self.effects.clear()
        self.detector.reset()
        self.pinch_mode = None
        self.kb_cell, self.kb_pinch = (0, 0), False
        self._fb_id = self.game.feedback_id
        self.screen_state = "game"

    def restart_level(self) -> None:
        self.game.reset()
        self.effects.clear()
        self.pinch_mode = None
        self.kb_pinch = False
        self._fb_id = self.game.feedback_id

    def next_level(self) -> None:
        if self.game.status == Status.WON:
            self.score_before += self.game.score
            if self.levels.advance():
                self.start_level()

    # ------------------------------------------------------------ buttons
    def current_buttons(self) -> List[Button]:
        ui, st = self.ui, self.screen_state
        if st == "menu":
            return ui.menu_buttons(self.settings, self.levels)
        if st == "camera":
            return ui.camera_buttons()
        if st == "final":
            cx = ui.w // 2
            return [Button("menu", pygame.Rect(cx - 160, 500, 320, 56), "Play again", primary=True),
                    Button("exit", pygame.Rect(cx - 160, 570, 320, 52), "Exit")]
        g = self.game
        if g.status == Status.PAUSED:
            return ui.overlay_buttons([("resume", "Resume", True, True),
                                       ("restart", "Restart", True, False),
                                       ("menu", "Menu", True, False),
                                       ("exit", "Exit", True, False)])
        if g.status == Status.WON:
            first = ("next", "Next Level", True, True) if self.levels.has_next \
                else ("finish", "Finish", True, True)
            return ui.overlay_buttons([first, ("restart", "Play again", True, False),
                                       ("menu", "Menu", True, False)])
        if g.status == Status.LOST:
            return ui.overlay_buttons([("restart", "Try again", True, True),
                                       ("menu", "Menu", True, False),
                                       ("exit", "Exit", True, False)])
        return ui.game_buttons(g, self.levels.has_next)

    @staticmethod
    def button_at(pos, buttons) -> Optional[Button]:
        if pos is None:
            return None
        for b in buttons:
            if b.rect.collidepoint(pos):
                return b
        return None

    def activate(self, bid: str) -> None:
        g = self.game
        if bid == "start":
            self.begin(1)
        elif bid.startswith("level_"):
            self.begin(int(bid.split("_")[1]))
        elif bid == "difficulty":
            self.settings.cycle_difficulty()
        elif bid == "animations":
            self.settings.animations = not self.settings.animations
            self.effects.enabled = self.settings.animations
            self.effects.clear()
        elif bid == "preview":
            self.settings.show_preview = not self.settings.show_preview
        elif bid == "keyboard":
            self.settings.keyboard_mode = not self.settings.keyboard_mode
        elif bid == "exit":
            self.running = False
        elif bid == "pause":
            if g.status == Status.PAUSED:
                g.resume()
            else:
                g.pause()
        elif bid == "resume":
            g.resume()
        elif bid == "restart":
            self.restart_level()
        elif bid == "next":
            self.next_level()
        elif bid == "finish":
            self.screen_state = "final"
            self.effects.celebrate(pygame.Rect(0, 0, *S.WINDOW_SIZE))
        elif bid == "menu":
            self.screen_state = "menu"
            self.effects.clear()
        elif bid == "retry":
            self.tracker.retry()
        elif bid == "use_keyboard":
            self.settings.keyboard_mode = True
            self.after_camera_ready()

    def after_camera_ready(self) -> None:
        if self.camera_return == "resume" and self.game is not None:
            self.screen_state = "game"      # still paused: the player presses Resume
        else:
            self.start_level()

    # -------------------------------------------------------------- input
    def read_pointer(self):
        """Returns (position, pinching, pinch_started, pinch_ended)."""
        w, h = self.ui.w, self.ui.h
        if self.settings.keyboard_mode:
            pos = None
            if self.screen_state == "game" and self.view is not None:
                pos = self.view.center(self.kb_cell)
            started, ended = self._kb_started, self._kb_ended
            self._kb_started = self._kb_ended = False
            self.hand_seen = True
            return pos, self.kb_pinch, started, ended
        obs = self.tracker.latest() if self.tracker.status == "running" else None
        state = self.detector.update(obs, time.monotonic())
        self.hand_seen = state.hand_visible
        pos = None
        if state.cursor is not None:
            pos = (state.cursor[0] * w, state.cursor[1] * h)
        return pos, state.pinching, state.pinch_started, state.pinch_ended

    def handle_pointer(self, pos, pinching, started, ended) -> None:
        buttons = self.current_buttons()
        g = self.game
        if started:
            b = self.button_at(pos, buttons)
            if b is not None:
                self.pinch_mode = "button"
                if b.enabled:
                    self.activate(b.id)
            elif self.screen_state == "game" and g.accepting_input:
                self.pinch_mode = "draw" if g.begin_path(self.view.cell_at(pos)) else None
            else:
                self.pinch_mode = None
        elif pinching and self.pinch_mode == "draw" and self.screen_state == "game":
            g.move_to(self.view.cell_at(pos))
        if ended:
            if self.pinch_mode == "draw" and self.game is not None:
                self.game.end_path()
            self.pinch_mode = None

    def handle_key(self, key) -> None:
        st = self.screen_state
        g = self.game
        if st == "menu":
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.begin(1)
            elif key == pygame.K_ESCAPE:
                self.running = False
        elif st == "camera":
            if key == pygame.K_ESCAPE:
                self.screen_state = "menu"
        elif st == "final":
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.screen_state = "menu"
            elif key == pygame.K_ESCAPE:
                self.running = False
        elif st == "game":
            if key in (pygame.K_ESCAPE, pygame.K_p):
                if g.status == Status.PAUSED:
                    g.resume()
                else:
                    g.pause()
            elif key == pygame.K_r:
                self.restart_level()
            elif key == pygame.K_n and g.status == Status.WON:
                if self.levels.has_next:
                    self.next_level()
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if g.status == Status.PAUSED:
                    g.resume()
                elif g.status == Status.WON:
                    self.activate("next" if self.levels.has_next else "finish")
                elif g.status == Status.LOST:
                    self.restart_level()
            elif self.settings.keyboard_mode and g.accepting_input:
                self.keyboard_cursor(key)

    def keyboard_cursor(self, key) -> None:
        moves = {pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0),
                 pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1)}
        if key in moves:
            dx, dy = moves[key]
            lv = self.game.level
            self.kb_cell = (min(lv.width - 1, max(0, self.kb_cell[0] + dx)),
                            min(lv.height - 1, max(0, self.kb_cell[1] + dy)))
        elif key == pygame.K_SPACE:
            if self.kb_pinch:
                self.kb_pinch, self._kb_ended = False, True
            else:
                self.kb_pinch, self._kb_started = True, True

    # ------------------------------------------------------------- update
    def update(self, dt: float) -> None:
        if self.screen_state == "camera":
            if self.tracker.status == "running":
                self.after_camera_ready()
        elif self.screen_state == "game":
            g = self.game
            if (not self.settings.keyboard_mode and self.tracker.status == "error"):
                g.pause()
                self.camera_return = "resume"
                self.screen_state = "camera"
            g.update(dt)
            if g.feedback_id != self._fb_id:
                self._fb_id = g.feedback_id
                self.on_feedback(g.feedback)
            if g.status != Status.PLAYING and g.status != Status.READY:
                self.kb_pinch = False
        self.effects.update(dt)

    def on_feedback(self, fb) -> None:
        color = S.COLOR_RGB.get(fb.color, S.TEXT) if fb.color else S.TEXT
        if fb.kind == "invalid" and fb.cell is not None:
            self.effects.ring(self.view.center(fb.cell), S.SOFT_WARN)
        elif fb.kind == "complete":
            self.effects.sparkle(self.view.center(self.game.paths[fb.color][-1]), color)
        elif fb.kind == "win":
            self.levels.complete_level(self.game.level.number)
            self.effects.celebrate(pygame.Rect(0, 0, *S.WINDOW_SIZE))

    # --------------------------------------------------------------- draw
    def draw(self, hover_id: Optional[str], buttons: List[Button]) -> None:
        ui, st = self.ui, self.screen_state
        if st == "menu":
            ui.draw_menu(buttons, hover_id, self.tracker.status, self.settings.keyboard_mode,
                         self.tracker.error_message)
        elif st == "camera":
            ui.draw_camera_screen(self.tracker.status, self.tracker.error_message,
                                  buttons, hover_id)
        elif st == "final":
            ui.draw_final(buttons, hover_id, self.effects, self.settings.animations)
            self.effects.draw(self.screen)
        else:
            self.draw_game(hover_id, buttons)
        active = self.game.active_color if (st == "game" and self.game) else None
        ui.cursor(self.pointer if not self.settings.keyboard_mode or st != "game" else None,
                  self.pinching, S.COLOR_RGB.get(active) if active else None)
        pygame.display.flip()

    def draw_game(self, hover_id, buttons) -> None:
        ui, g = self.ui, self.game
        ui.background()
        hover_cell = self.view.cell_at(self.pointer) if self.pointer else None
        if self.settings.keyboard_mode:
            hover_cell = self.kb_cell
        ui.draw_board(g, self.view, hover_cell)
        overlay = g.status in (Status.PAUSED, Status.WON, Status.LOST)
        preview = None
        if self.settings.show_preview and not self.settings.keyboard_mode:
            data = self.tracker.preview()
            if data is not None:
                preview = pygame.image.frombuffer(data[0], data[1], "RGB")
        ui.draw_hud(g, self.score_before, [] if overlay else buttons, hover_id,
                    self.settings.keyboard_mode, preview, self.hand_seen,
                    self.settings.show_preview)
        if g.status == Status.PAUSED:
            ui.overlay("Paused", "Take your time. Press Resume when you are ready.",
                       buttons, hover_id)
        elif g.status == Status.WON:
            msg = g.feedback.message if self.levels.has_next else \
                "Wonderful! You finished the very last level!"
            still = None if self.settings.animations else self.effects.draw_still_celebration
            ui.overlay("Level complete!", msg, buttons, hover_id, still)
        elif g.status == Status.LOST:
            ui.overlay("Time is up", g.feedback.message, buttons, hover_id)
        self.effects.draw(self.screen)

    # ---------------------------------------------------------------- run
    def run(self) -> None:
        try:
            while self.running:
                dt = min(self.clock.tick(S.FPS) / 1000.0, 0.1)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    elif event.type == pygame.KEYDOWN:
                        self.handle_key(event.key)
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        b = self.button_at(event.pos, self.current_buttons())
                        if b is not None and b.enabled:
                            self.activate(b.id)
                pos, pinching, started, ended = self.read_pointer()
                self.pointer = pos
                self.pinching = pinching
                self.handle_pointer(pos, pinching, started, ended)
                self.update(dt)
                buttons = self.current_buttons()
                hover_pos = pos if pos is not None else pygame.mouse.get_pos()
                hover = self.button_at(hover_pos, buttons)
                self.draw(hover.id if hover else None, buttons)
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        """Release the webcam and close the window."""
        try:
            self.tracker.stop()
        finally:
            pygame.quit()


def main() -> int:
    App().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
