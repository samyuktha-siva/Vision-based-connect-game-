"""Rules, score and timer for one level. No Pygame or webcam code in here."""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set

from game.board import Board, Cell, LevelData, adjacent
from game.settings import PAIR_POINTS


class Status(Enum):
    READY = "Ready"        # level loaded, timer waits for the first pinch on a dot
    PLAYING = "Playing"
    PAUSED = "Paused"
    WON = "Level complete"
    LOST = "Time is up"


@dataclass
class Feedback:
    kind: str                       # info, start, complete, invalid, cancel, win, lose
    message: str
    cell: Optional[Cell] = None
    color: Optional[str] = None


MESSAGES = {
    "blocked": "That square is blocked. Let's try another way!",
    "mismatch": "Those colours don't match. Try the same colour!",
    "occupied": "A path is already there. Try a different way!",
    "no_dot": "Pinch on a dot to start.",
    "cancel": "No problem! Pinch a dot to try again.",
    "win": "Wonderful! You did it! Let's explore the next level!",
    "lose": "Great effort! Every try helps you learn. Would you like to try again?",
}


class GameState:
    """One play-through of one level."""

    def __init__(self, level: LevelData, time_limit: Optional[float] = None):
        self.level = level
        self.board = Board(level)
        self.time_limit = float(time_limit if time_limit is not None else level.time_limit)
        self.reset()

    # ------------------------------------------------------------ set up
    def reset(self) -> None:
        """Restart the level: clears connections, score and timer."""
        self.paths: Dict[str, List[Cell]] = {}
        self.completed: Set[str] = set()
        self._scored: Set[str] = set()
        self.active_color: Optional[str] = None
        self.score = 0
        self.time_left = self.time_limit
        self.status = Status.READY
        self._paused_from = Status.READY
        self.feedback = Feedback("info", "Pinch a dot, then move to its partner.")
        self.feedback_id = 0

    def _say(self, kind: str, message: str, cell: Optional[Cell] = None,
             color: Optional[str] = None) -> None:
        self.feedback = Feedback(kind, message, cell, color)
        self.feedback_id += 1

    # --------------------------------------------------------- read-only
    @property
    def pairs_total(self) -> int:
        return len(self.level.dots)

    @property
    def pairs_done(self) -> int:
        return len(self.completed)

    @property
    def accepting_input(self) -> bool:
        return self.status in (Status.READY, Status.PLAYING)

    def occupied_by_others(self, color: str) -> Set[Cell]:
        cells: Set[Cell] = set()
        for other, path in self.paths.items():
            if other != color:
                cells.update(path)
        return cells

    # ------------------------------------------------------ pause / time
    def pause(self) -> bool:
        if self.status in (Status.READY, Status.PLAYING):
            self._paused_from = self.status
            self.status = Status.PAUSED
            self.active_color = None
            return True
        return False

    def resume(self) -> bool:
        if self.status == Status.PAUSED:
            self.status = self._paused_from
            return True
        return False

    def update(self, dt: float) -> None:
        """Advance the timer. Only runs while PLAYING."""
        if self.status != Status.PLAYING:
            return
        self.time_left -= dt
        if self.time_left <= 0:
            self.time_left = 0.0
            self.status = Status.LOST
            self.active_color = None
            self._say("lose", MESSAGES["lose"])

    # ------------------------------------------------------------ drawing
    def begin_path(self, cell: Optional[Cell]) -> bool:
        """A pinch started over `cell`. Only a dot can start a path."""
        if not self.accepting_input or cell is None or not self.board.in_bounds(cell):
            return False
        color = self.board.dot_at(cell)
        if color is None:
            self._say("info", MESSAGES["no_dot"], cell)
            return False
        self.paths[color] = [cell]       # starting again clears the old path
        self.completed.discard(color)
        self.active_color = color
        if self.status == Status.READY:
            self.status = Status.PLAYING
        self._say("start", "Now move to the matching dot.", cell, color)
        return True

    def move_to(self, cell: Optional[Cell]) -> bool:
        """The pinch moved over `cell`. Extends the path one square at a time,
        so a fast finger movement cannot jump over obstacles."""
        if self.status != Status.PLAYING or self.active_color is None:
            return False
        if cell is None or not self.board.in_bounds(cell):
            return False
        color = self.active_color
        while self.active_color == color and self.paths[color][-1] != cell:
            step = self._step_toward(self.paths[color][-1], cell)
            if not self._try_step(color, step):
                return False
        return True

    @staticmethod
    def _step_toward(src: Cell, dst: Cell) -> Cell:
        dx, dy = dst[0] - src[0], dst[1] - src[1]
        if abs(dx) >= abs(dy):
            return (src[0] + (1 if dx > 0 else -1), src[1])
        return (src[0], src[1] + (1 if dy > 0 else -1))

    def _try_step(self, color: str, cell: Cell) -> bool:
        path = self.paths[color]
        if not adjacent(path[-1], cell):
            return False
        if self.board.is_obstacle(cell):
            self._say("invalid", MESSAGES["blocked"], cell, color)
            return False
        if cell in path:                  # going back along the own path
            del path[path.index(cell) + 1:]
            return True
        dot = self.board.dot_at(cell)
        if dot is not None and dot != color:
            self._say("invalid", MESSAGES["mismatch"], cell, color)
            return False
        if cell in self.occupied_by_others(color):
            self._say("invalid", MESSAGES["occupied"], cell, color)
            return False
        path.append(cell)
        if dot == color:                  # the partner dot (own start is in `path`)
            self._complete(color)
        return True

    def _complete(self, color: str) -> None:
        self.completed.add(color)
        self.active_color = None
        if color not in self._scored:     # never score a pair twice
            self._scored.add(color)
            self.score += PAIR_POINTS
        if len(self.completed) == self.pairs_total:
            self.score += int(self.time_left)       # small bonus for time left
            self.status = Status.WON
            self._say("win", MESSAGES["win"], color=color)
        else:
            self._say("complete", f"Great! {color.capitalize()} is connected!",
                      color=color)

    def end_path(self) -> None:
        """The pinch was released. Unfinished paths are removed gently."""
        color = self.active_color
        if color is None:
            return
        self.active_color = None
        if color not in self.completed:
            self.paths.pop(color, None)
            self._say("cancel", MESSAGES["cancel"])
