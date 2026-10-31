from game.game_logic import GameState, Status
from game.settings import PAIR_POINTS


def draw(game, path):
    """Pinch on the first cell and move cell by cell along the path."""
    assert game.begin_path(path[0])
    for cell in path[1:]:
        game.move_to(cell)


def test_matching_colours_connect(small_level):
    g = GameState(small_level)
    draw(g, [(0, 0), (1, 0), (2, 0), (3, 0)])
    assert "red" in g.completed
    assert g.pairs_done == 1


def test_path_can_start_from_either_dot(small_level):
    g = GameState(small_level)
    draw(g, [(3, 0), (2, 0), (1, 0), (0, 0)])
    assert "red" in g.completed


def test_wrong_colour_is_rejected(small_level):
    g = GameState(small_level)
    g.begin_path((0, 0))
    g.move_to((0, 1))
    assert g.move_to((0, 2)) is False          # (0,2) is a blue dot
    assert g.feedback.kind == "invalid"
    assert "colours don't match" in g.feedback.message
    assert g.completed == set()
    assert g.paths["red"][-1] == (0, 1)        # stopped before the blue dot


def test_pinch_must_start_on_a_dot(small_level):
    g = GameState(small_level)
    assert g.begin_path((2, 2)) is False       # empty cell
    assert g.begin_path((1, 1)) is False       # obstacle
    assert g.begin_path((9, 9)) is False       # outside the board
    assert g.begin_path(None) is False
    assert g.paths == {}
    assert g.status == Status.READY


def test_obstacle_blocks_movement(small_level):
    g = GameState(small_level)
    g.begin_path((0, 0))
    g.move_to((0, 1))
    assert g.move_to((1, 1)) is False
    assert (1, 1) not in g.paths["red"]
    assert "blocked" in g.feedback.message


def test_fast_movement_cannot_jump_over_an_obstacle(small_level):
    g = GameState(small_level)
    g.begin_path((0, 0))
    g.move_to((0, 1))
    # Finger jumps straight to (2,1): the walk goes through the obstacle (1,1)
    assert g.move_to((2, 1)) is False
    assert (2, 1) not in g.paths["red"]


def test_cannot_cross_another_path():
    from game.board import LevelData
    level = LevelData(0, 3, 3, frozenset(), {"red": ((0, 0), (2, 0)), "blue": ((1, 0), (1, 2))},
                      60.0, {})
    g = GameState(level)
    draw(g, [(1, 0), (1, 1), (1, 2)])           # blue goes down the middle
    assert g.pairs_done == 1
    g.begin_path((0, 0))
    g.move_to((0, 1))
    assert g.move_to((1, 1)) is False           # that square already has a path
    assert (1, 1) not in g.paths["red"]
    assert "already there" in g.feedback.message


def test_cannot_walk_through_a_dot_of_another_colour(small_level):
    g = GameState(small_level)
    g.begin_path((3, 0))
    g.move_to((3, 1))
    assert g.move_to((3, 2)) is False           # blue dot
    assert (3, 2) not in g.paths["red"]


def test_score_only_for_new_completed_pairs(small_level):
    g = GameState(small_level)
    assert g.score == 0
    draw(g, [(0, 0), (1, 0), (2, 0), (3, 0)])
    assert g.score == PAIR_POINTS
    # An invalid attempt does not change the score
    g.begin_path((0, 2))
    g.move_to((1, 1))
    assert g.score == PAIR_POINTS


def test_duplicate_connection_is_not_scored_twice(small_level):
    g = GameState(small_level)
    draw(g, [(0, 0), (1, 0), (2, 0), (3, 0)])
    assert g.score == PAIR_POINTS
    draw(g, [(0, 0), (1, 0), (2, 0), (3, 0)])   # connect the same pair again
    assert g.pairs_done == 1
    assert g.score == PAIR_POINTS


def test_releasing_early_cancels_the_path(small_level):
    g = GameState(small_level)
    g.begin_path((0, 0))
    g.move_to((1, 0))
    g.end_path()
    assert "red" not in g.paths
    assert g.pairs_done == 0
    assert g.feedback.kind == "cancel"


def test_releasing_after_completion_keeps_the_path(small_level):
    g = GameState(small_level)
    draw(g, [(0, 0), (1, 0), (2, 0), (3, 0)])
    g.end_path()
    assert g.paths["red"] == [(0, 0), (1, 0), (2, 0), (3, 0)]


def test_moving_back_shortens_the_path(small_level):
    g = GameState(small_level)
    g.begin_path((0, 0))
    g.move_to((2, 0))
    g.move_to((1, 0))
    assert g.paths["red"] == [(0, 0), (1, 0)]


def test_winning_requires_every_pair(small_level):
    g = GameState(small_level)
    draw(g, [(0, 0), (1, 0), (2, 0), (3, 0)])
    assert g.status == Status.PLAYING
    draw(g, [(0, 2), (1, 2), (2, 2), (3, 2)])
    assert g.status == Status.WON
    assert g.feedback.message == "Wonderful! You did it! Let's explore the next level!"
    assert g.accepting_input is False


def test_timer_stops_on_win(small_level):
    g = GameState(small_level)
    draw(g, [(0, 0), (1, 0), (2, 0), (3, 0)])
    g.update(5)
    draw(g, [(0, 2), (1, 2), (2, 2), (3, 2)])
    left = g.time_left
    g.update(10)
    assert g.time_left == left


def test_timer_waits_for_first_pinch(small_level):
    g = GameState(small_level)
    g.update(10)
    assert g.time_left == 60.0
    g.begin_path((0, 0))
    g.update(10)
    assert g.time_left == 50.0


def test_timer_pause_and_resume(small_level):
    g = GameState(small_level)
    g.begin_path((0, 0))
    g.update(10)
    assert g.pause() is True
    assert g.status == Status.PAUSED
    g.update(30)                                 # time passes while paused
    assert g.time_left == 50.0
    assert g.resume() is True
    assert g.status == Status.PLAYING
    g.update(5)
    assert g.time_left == 45.0


def test_pause_blocks_drawing(small_level):
    g = GameState(small_level)
    g.begin_path((0, 0))
    g.pause()
    assert g.move_to((1, 0)) is False
    assert g.begin_path((0, 2)) is False


def test_resume_without_pause_does_nothing(small_level):
    g = GameState(small_level)
    assert g.resume() is False
    assert g.status == Status.READY


def test_time_expiry_loses_with_kind_message(small_level):
    g = GameState(small_level)
    g.begin_path((0, 0))
    g.update(59)
    assert g.status == Status.PLAYING
    g.update(2)
    assert g.status == Status.LOST
    assert g.time_left == 0
    assert g.feedback.message == ("Great effort! Every try helps you learn. "
                                  "Would you like to try again?")
    assert g.begin_path((0, 2)) is False         # no play after time is up


def test_restart_resets_everything(small_level):
    g = GameState(small_level)
    draw(g, [(0, 0), (1, 0), (2, 0), (3, 0)])
    g.update(20)
    g.reset()
    assert g.paths == {} and g.completed == set()
    assert g.score == 0
    assert g.time_left == g.time_limit
    assert g.status == Status.READY
    draw(g, [(0, 0), (1, 0), (2, 0), (3, 0)])    # scoring works again
    assert g.score == PAIR_POINTS


def test_restart_after_loss(small_level):
    g = GameState(small_level)
    g.begin_path((0, 0))
    g.update(100)
    assert g.status == Status.LOST
    g.reset()
    assert g.status == Status.READY and g.time_left == 60.0


def test_custom_time_limit(small_level):
    g = GameState(small_level, time_limit=120)
    assert g.time_left == 120
