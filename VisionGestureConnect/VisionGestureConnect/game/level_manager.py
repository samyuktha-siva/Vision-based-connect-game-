"""Ten levels (stored as plain data), a reproducible level builder and unlock tracking.

Each level is described by a small LevelConfig. The builder uses the config's
`seed`, so the same level is produced every time. It works by drawing the
solution FIRST (random non-overlapping paths on the free cells), then putting
the dots at the path ends. That guarantees every level can be solved.
"""

import json
import random
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Optional

from game.board import Cell, LevelData
from game.settings import COLOR_NAMES


@dataclass(frozen=True)
class LevelConfig:
    number: int
    width: int
    height: int
    pairs: int
    obstacles: int
    min_len: int        # shortest route (in cells) used for the stored solution
    max_len: int
    time_limit: int     # seconds
    seed: int


LEVEL_CONFIGS: List[LevelConfig] = [
    #            no  w  h  pairs obst min max time seed
    LevelConfig(1, 5, 5, 3, 0, 3, 5, 90, 101),
    LevelConfig(2, 5, 5, 3, 0, 4, 6, 90, 202),
    LevelConfig(3, 6, 6, 4, 0, 4, 6, 100, 303),
    LevelConfig(4, 6, 6, 4, 3, 4, 6, 110, 404),
    LevelConfig(5, 6, 6, 4, 6, 4, 7, 120, 505),
    LevelConfig(6, 7, 7, 5, 7, 4, 7, 130, 606),
    LevelConfig(7, 7, 7, 5, 9, 5, 8, 140, 707),
    LevelConfig(8, 7, 7, 5, 12, 5, 8, 150, 808),
    LevelConfig(9, 8, 8, 6, 14, 5, 8, 165, 909),
    LevelConfig(10, 8, 8, 6, 16, 5, 8, 180, 1010),
]


def _random_path(rng: random.Random, free: set, min_len: int, max_len: int,
                 tries: int = 300) -> Optional[List[Cell]]:
    """A random walk over free cells that never revisits a cell."""
    cells = sorted(free)
    if not cells:
        return None
    for _ in range(tries):
        length = rng.randint(min_len, max_len)
        path = [rng.choice(cells)]
        used = {path[0]}
        while len(path) < length:
            x, y = path[-1]
            options = [c for c in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
                       if c in free and c not in used]
            if not options:
                break
            nxt = rng.choice(options)
            path.append(nxt)
            used.add(nxt)
        if len(path) == length:
            return path
    return None


def generate_level(cfg: LevelConfig) -> LevelData:
    """Build one level from its config. The same config always gives the same level."""
    rng = random.Random(cfg.seed)
    everything = [(x, y) for y in range(cfg.height) for x in range(cfg.width)]
    for _ in range(2000):
        obstacles = set(rng.sample(everything, cfg.obstacles)) if cfg.obstacles else set()
        free = set(everything) - obstacles
        solution: Dict[str, List[Cell]] = {}
        for color in COLOR_NAMES[:cfg.pairs]:
            path = _random_path(rng, free, cfg.min_len, cfg.max_len)
            if path is None:
                break
            solution[color] = path
            free -= set(path)
        if len(solution) == cfg.pairs:
            dots = {c: (p[0], p[-1]) for c, p in solution.items()}
            return LevelData(cfg.number, cfg.width, cfg.height, frozenset(obstacles),
                             dots, float(cfg.time_limit), solution)
    raise RuntimeError(f"Could not build level {cfg.number}")  # not expected


@lru_cache(maxsize=None)
def get_level(number: int) -> LevelData:
    """Level numbers go from 1 to 10."""
    if not 1 <= number <= len(LEVEL_CONFIGS):
        raise ValueError(f"No level {number}")
    return generate_level(LEVEL_CONFIGS[number - 1])


class LevelManager:
    """Tracks the current level and which levels are unlocked."""

    def __init__(self, save_path: Optional[str] = None):
        self.total = len(LEVEL_CONFIGS)
        self.unlocked = 1
        self.current = 1
        self.save_path = save_path
        self._load()

    def is_unlocked(self, number: int) -> bool:
        return 1 <= number <= self.unlocked

    def select(self, number: int) -> bool:
        if self.is_unlocked(number):
            self.current = number
            return True
        return False

    def complete_level(self, number: int) -> None:
        """Call this only when the player wins. Unlocks the next level."""
        if number < self.total and number + 1 > self.unlocked:
            self.unlocked = number + 1
            self._save()

    @property
    def has_next(self) -> bool:
        return self.current < self.total

    def advance(self) -> bool:
        """Move to the next level if there is one and it is unlocked."""
        if self.has_next and self.is_unlocked(self.current + 1):
            self.current += 1
            return True
        return False

    def level(self) -> LevelData:
        return get_level(self.current)

    # ---- saving progress (optional, failures are ignored) ----
    def _load(self) -> None:
        if not self.save_path:
            return
        try:
            with open(self.save_path, "r", encoding="utf-8") as f:
                value = int(json.load(f).get("unlocked", 1))
            self.unlocked = max(1, min(self.total, value))
        except (OSError, ValueError, TypeError, AttributeError):
            self.unlocked = 1

    def _save(self) -> None:
        if not self.save_path:
            return
        try:
            with open(self.save_path, "w", encoding="utf-8") as f:
                json.dump({"unlocked": self.unlocked}, f)
        except OSError:
            pass
