import json

import pytest

from game.board import Board, validate_solution
from game.level_manager import LEVEL_CONFIGS, LevelManager, generate_level, get_level
from game.game_logic import GameState, Status


def test_there_are_ten_levels():
    assert len(LEVEL_CONFIGS) == 10
    assert [c.number for c in LEVEL_CONFIGS] == list(range(1, 11))


def test_first_level_has_three_pairs_and_no_obstacles():
    level = get_level(1)
    assert len(level.dots) == 3
    assert len(level.obstacles) == 0


@pytest.mark.parametrize("n", range(1, 11))
def test_every_level_is_solvable(n):
    level = get_level(n)
    assert validate_solution(level, level.solution)


@pytest.mark.parametrize("n", range(1, 11))
def test_level_layout_is_sound(n):
    level = get_level(n)
    cfg = LEVEL_CONFIGS[n - 1]
    board = Board(level)
    assert (level.width, level.height) == (cfg.width, cfg.height)
    assert len(level.dots) == cfg.pairs
    assert len(level.obstacles) == cfg.obstacles
    seen = set()
    for color, (a, b) in level.dots.items():
        assert a != b
        for cell in (a, b):
            assert board.in_bounds(cell)
            assert cell not in level.obstacles          # dots never on obstacles
            assert cell not in seen                     # dots never overlap
            seen.add(cell)
    for path in level.solution.values():
        assert not set(path) & level.obstacles          # solution avoids obstacles
    assert level.time_limit >= 90


@pytest.mark.parametrize("n", range(1, 11))
def test_solution_plays_through_the_game_logic(n):
    level = get_level(n)
    g = GameState(level)
    for path in level.solution.values():
        assert g.begin_path(path[0])
        for cell in path[1:]:
            assert g.move_to(cell)
    assert g.status == Status.WON
    assert g.pairs_done == len(level.dots)


def test_levels_are_reproducible():
    for cfg in LEVEL_CONFIGS:
        a, b = generate_level(cfg), generate_level(cfg)
        assert a.obstacles == b.obstacles
        assert a.dots == b.dots
        assert a.solution == b.solution


def test_difficulty_increases_gradually():
    pairs = [c.pairs for c in LEVEL_CONFIGS]
    obstacles = [c.obstacles for c in LEVEL_CONFIGS]
    sizes = [c.width * c.height for c in LEVEL_CONFIGS]
    assert pairs == sorted(pairs) and obstacles == sorted(obstacles) and sizes == sorted(sizes)
    assert obstacles[0] == 0 and obstacles[-1] == max(obstacles)
    assert all(b - a <= 5 for a, b in zip(obstacles, obstacles[1:]))   # no sudden jumps


def test_level_range_is_checked():
    with pytest.raises(ValueError):
        get_level(0)
    with pytest.raises(ValueError):
        get_level(11)


def test_only_level_one_is_unlocked_at_the_start():
    m = LevelManager()
    assert m.is_unlocked(1)
    assert not any(m.is_unlocked(n) for n in range(2, 11))
    assert m.select(2) is False and m.current == 1
    assert m.advance() is False


def test_winning_unlocks_the_next_level():
    m = LevelManager()
    m.complete_level(1)
    assert m.is_unlocked(2) and not m.is_unlocked(3)
    assert m.advance() is True and m.current == 2
    assert m.select(1) is True


def test_unlock_does_not_go_backwards_or_past_ten():
    m = LevelManager()
    m.complete_level(1)
    m.complete_level(2)
    m.complete_level(1)
    assert m.unlocked == 3
    for n in range(1, 11):
        m.complete_level(n)
    assert m.unlocked == 10
    m.select(10)
    assert m.has_next is False and m.advance() is False


def test_progress_is_saved_and_loaded(tmp_path):
    path = str(tmp_path / "progress.json")
    m = LevelManager(path)
    m.complete_level(1)
    m.complete_level(2)
    assert LevelManager(path).unlocked == 3


def test_broken_progress_file_is_ignored(tmp_path):
    path = tmp_path / "progress.json"
    path.write_text("not json")
    assert LevelManager(str(path)).unlocked == 1
    path.write_text(json.dumps({"unlocked": 999}))
    assert LevelManager(str(path)).unlocked == 10
