import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from game.board import LevelData


@pytest.fixture
def small_level():
    """4 wide, 3 high. One obstacle in the middle. Two pairs: red (top) and blue (bottom)."""
    return LevelData(
        number=0, width=4, height=3, obstacles=frozenset({(1, 1)}),
        dots={"red": ((0, 0), (3, 0)), "blue": ((0, 2), (3, 2))},
        time_limit=60.0,
        solution={"red": [(0, 0), (1, 0), (2, 0), (3, 0)],
                  "blue": [(0, 2), (1, 2), (2, 2), (3, 2)]},
    )
