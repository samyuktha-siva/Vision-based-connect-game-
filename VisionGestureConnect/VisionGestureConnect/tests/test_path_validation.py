from game.board import Board, adjacent, validate_path, validate_solution


def test_valid_straight_path(small_level):
    path = [(0, 0), (1, 0), (2, 0), (3, 0)]
    assert validate_path(small_level, "red", path).ok


def test_valid_path_from_either_end(small_level):
    assert validate_path(small_level, "red", [(3, 0), (2, 0), (1, 0), (0, 0)]).ok


def test_path_around_obstacle(small_level):
    path = [(0, 0), (0, 1), (0, 2)]
    assert validate_path(small_level, "red", path).reason == "mismatch"  # ends on blue


def test_obstacle_collision(small_level):
    r = validate_path(small_level, "red", [(0, 0), (0, 1), (1, 1), (2, 1), (3, 1), (3, 0)])
    assert not r.ok and r.reason == "blocked"


def test_diagonal_step_is_invalid(small_level):
    r = validate_path(small_level, "red", [(0, 0), (1, 0), (2, 0), (3, 1), (3, 0)])
    assert not r.ok and r.reason == "not_adjacent"


def test_gap_in_path_is_invalid(small_level):
    r = validate_path(small_level, "red", [(0, 0), (2, 0), (3, 0)])
    assert not r.ok and r.reason == "not_adjacent"


def test_must_start_on_a_dot(small_level):
    r = validate_path(small_level, "red", [(1, 0), (2, 0), (3, 0)])
    assert not r.ok and r.reason == "bad_start"


def test_must_end_on_partner(small_level):
    r = validate_path(small_level, "red", [(0, 0), (1, 0), (2, 0)])
    assert not r.ok and r.reason == "wrong_end"


def test_mismatched_colours_rejected(small_level):
    r = validate_path(small_level, "red", [(0, 0), (0, 1), (0, 2)])
    assert not r.ok and r.reason == "mismatch"


def test_cannot_pass_over_other_dot(small_level):
    r = validate_path(small_level, "red", [(0, 0), (0, 1), (0, 2), (1, 2), (2, 2), (3, 2),
                                           (3, 1), (3, 0)])
    assert not r.ok and r.reason == "crosses_dot"


def test_repeated_cell_invalid(small_level):
    r = validate_path(small_level, "red", [(0, 0), (1, 0), (0, 0)])
    assert not r.ok and r.reason == "repeated_cell"


def test_out_of_bounds(small_level):
    r = validate_path(small_level, "red", [(3, 0), (4, 0)])
    assert not r.ok and r.reason == "out_of_bounds"


def test_overlap_with_other_path(small_level):
    path = [(0, 0), (1, 0), (2, 0), (3, 0)]
    r = validate_path(small_level, "red", path, occupied=[(2, 0)])
    assert not r.ok and r.reason == "overlap"


def test_too_short_and_unknown_colour(small_level):
    assert validate_path(small_level, "red", [(0, 0)]).reason == "too_short"
    assert validate_path(small_level, "purple", [(0, 0), (1, 0)]).reason == "unknown_color"


def test_validate_solution(small_level):
    assert validate_solution(small_level, small_level.solution)
    missing = {"red": small_level.solution["red"]}
    assert not validate_solution(small_level, missing)


def test_solution_paths_may_not_overlap(small_level):
    bad = {"red": [(0, 0), (1, 0), (2, 0), (3, 0)],
           "blue": [(0, 2), (1, 2), (2, 2), (3, 2)]}
    assert validate_solution(small_level, bad)
    bad["blue"] = [(0, 2), (0, 1), (0, 0)]
    assert not validate_solution(small_level, bad)


def test_board_helpers(small_level):
    b = Board(small_level)
    assert b.in_bounds((3, 2)) and not b.in_bounds((4, 0)) and not b.in_bounds((-1, 0))
    assert b.is_obstacle((1, 1)) and not b.is_obstacle((0, 0))
    assert b.dot_at((0, 0)) == "red" and b.dot_at((1, 0)) is None
    assert b.other_end("red", (0, 0)) == (3, 0)
    assert adjacent((0, 0), (0, 1)) and not adjacent((0, 0), (1, 1))
