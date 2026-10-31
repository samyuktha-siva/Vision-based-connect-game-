"""Grid, level data and path validation. No Pygame or webcam code in here."""

from dataclasses import dataclass
from typing import Dict, FrozenSet, Iterable, List, Optional, Tuple

Cell = Tuple[int, int]  # (column, row), starting at (0, 0) in the top-left


@dataclass(frozen=True, eq=False)
class LevelData:
    """Everything that describes one level."""

    number: int
    width: int
    height: int
    obstacles: FrozenSet[Cell]
    dots: Dict[str, Tuple[Cell, Cell]]   # colour name -> its two dots
    time_limit: float                     # seconds
    solution: Dict[str, List[Cell]]       # one known valid solution


@dataclass(frozen=True)
class PathCheck:
    ok: bool
    reason: str = "ok"


def adjacent(a: Cell, b: Cell) -> bool:
    """True when two cells touch side to side (no diagonals)."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1


class Board:
    """Read-only questions about a level's grid."""

    def __init__(self, level: LevelData):
        self.level = level
        self._dot_at: Dict[Cell, str] = {}
        for color, (a, b) in level.dots.items():
            self._dot_at[a] = color
            self._dot_at[b] = color

    def in_bounds(self, cell: Cell) -> bool:
        return 0 <= cell[0] < self.level.width and 0 <= cell[1] < self.level.height

    def is_obstacle(self, cell: Cell) -> bool:
        return cell in self.level.obstacles

    def dot_at(self, cell: Cell) -> Optional[str]:
        return self._dot_at.get(cell)

    def other_end(self, color: str, cell: Cell) -> Cell:
        a, b = self.level.dots[color]
        return b if cell == a else a

    def all_cells(self) -> List[Cell]:
        return [(x, y) for y in range(self.level.height) for x in range(self.level.width)]


def validate_path(level: LevelData, color: str, path: List[Cell],
                  occupied: Iterable[Cell] = ()) -> PathCheck:
    """Check a finished path joining the two dots of `color`.

    Rules:
      1. It starts on one dot of the colour and ends on the other.
      2. Each step moves one cell up, down, left or right.
      3. It stays on the grid, never enters an obstacle, never repeats a cell.
      4. It never passes over any dot (a dot of another colour is a mismatch).
      5. It never uses a cell that already belongs to another path (`occupied`).
    """
    board = Board(level)
    if color not in level.dots:
        return PathCheck(False, "unknown_color")
    if len(path) < 2:
        return PathCheck(False, "too_short")
    first, last = level.dots[color]
    if path[0] not in (first, last):
        return PathCheck(False, "bad_start")
    expected_end = last if path[0] == first else first
    occupied_set = set(occupied)
    seen = set()
    for i, cell in enumerate(path):
        if not board.in_bounds(cell):
            return PathCheck(False, "out_of_bounds")
        if board.is_obstacle(cell):
            return PathCheck(False, "blocked")
        if cell in seen:
            return PathCheck(False, "repeated_cell")
        seen.add(cell)
        if i > 0 and not adjacent(path[i - 1], cell):
            return PathCheck(False, "not_adjacent")
        dot = board.dot_at(cell)
        if dot is not None and dot != color:
            return PathCheck(False, "mismatch" if i == len(path) - 1 else "crosses_dot")
        if cell == expected_end and i != len(path) - 1:
            return PathCheck(False, "crosses_dot")
        if cell in occupied_set:
            return PathCheck(False, "overlap")
    if path[-1] != expected_end:
        return PathCheck(False, "wrong_end")
    return PathCheck(True)


def validate_solution(level: LevelData, paths: Dict[str, List[Cell]]) -> bool:
    """True only if every pair is connected and no two paths share a cell."""
    used: set = set()
    for color in level.dots:
        path = paths.get(color)
        if not path:
            return False
        if not validate_path(level, color, path, used).ok:
            return False
        used.update(path)
    return True
