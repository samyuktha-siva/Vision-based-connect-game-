from types import SimpleNamespace

from vision.gesture_detector import (GestureDetector, HandObservation, map_to_window,
                                     pinch_ratio)
from vision.hand_tracker import observation_from_landmarks


def hand(pinched, x=0.5, y=0.5):
    """A made-up hand. Palm length is 0.2; fingertip gap is tiny when pinched."""
    gap = 0.01 if pinched else 0.2
    return HandObservation(index_tip=(x + gap / 2, y), thumb_tip=(x - gap / 2, y),
                           wrist=(x, y + 0.3), middle_mcp=(x, y + 0.1), aspect=1.0)


def detector(**kw):
    defaults = dict(smoothing=1.0, lost_grace=0.5, margin=0.0)
    defaults.update(kw)
    return GestureDetector(**defaults)


def test_pinch_ratio_is_relative_to_hand_size():
    assert pinch_ratio(hand(True)) < 0.1
    assert pinch_ratio(hand(False)) > 0.9


def test_pinch_start_and_end_events():
    d = detector()
    s = d.update(hand(False), 0.0)
    assert not s.pinching and not s.pinch_started
    s = d.update(hand(True), 0.1)
    assert s.pinching and s.pinch_started
    s = d.update(hand(True), 0.2)
    assert s.pinching and not s.pinch_started
    s = d.update(hand(False), 0.3)
    assert not s.pinching and s.pinch_ended


def test_hysteresis_prevents_flicker():
    d = detector(start_ratio=0.3, release_ratio=0.5)
    d.update(hand(True), 0.0)
    middle = hand(True)
    middle.index_tip = (0.5 + 0.04, 0.5)       # ratio 0.4: between the two thresholds
    middle.thumb_tip = (0.5 - 0.04, 0.5)
    assert d.update(middle, 0.1).pinching       # still pinching
    d2 = detector(start_ratio=0.3, release_ratio=0.5)
    assert not d2.update(middle, 0.0).pinching  # and an open hand does not start one


def test_cursor_is_the_pinch_point_and_maps_to_window():
    d = detector(margin=0.1)
    s = d.update(hand(False, x=0.5, y=0.5), 0.0)
    assert abs(s.cursor[0] - 0.5) < 1e-6 and abs(s.cursor[1] - 0.5) < 1e-6
    assert map_to_window((0.0, 1.0), 0.1) == (0.0, 1.0)      # clamped to the edges
    assert map_to_window((0.1, 0.9), 0.1) == (0.0, 1.0)


def test_smoothing_reduces_jitter():
    d = detector(smoothing=0.3)
    d.update(hand(False, x=0.4), 0.0)
    s = d.update(hand(False, x=0.6), 0.1)
    assert 0.4 < s.cursor[0] < 0.5               # moved only part of the way


def test_missing_hand_at_start():
    s = detector().update(None, 0.0)
    assert not s.hand_visible and s.cursor is None and not s.pinching


def test_short_tracking_loss_keeps_the_pinch():
    d = detector()
    d.update(hand(True), 0.0)
    s = d.update(None, 0.2)
    assert s.pinching and not s.pinch_ended and not s.hand_visible and s.cursor is not None


def test_long_tracking_loss_releases_the_pinch():
    d = detector()
    d.update(hand(True), 0.0)
    s = d.update(None, 1.0)
    assert s.pinch_ended and not s.pinching and s.cursor is None
    s = d.update(None, 1.1)
    assert not s.pinch_ended                      # only reported once


def test_observation_from_landmarks():
    lm = [SimpleNamespace(x=i / 100, y=i / 50) for i in range(21)]
    obs = observation_from_landmarks(lm, 4 / 3, 1.5)
    assert obs.index_tip == (0.08, 0.16) and obs.thumb_tip == (0.04, 0.08)
    assert obs.wrist == (0.0, 0.0) and obs.middle_mcp == (0.09, 0.18)
    assert obs.timestamp == 1.5
