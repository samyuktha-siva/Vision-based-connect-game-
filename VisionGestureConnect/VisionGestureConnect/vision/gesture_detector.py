"""Turns hand landmarks into a cursor and pinch events. No webcam code in here,
so it can be tested with made-up numbers."""

import math
from dataclasses import dataclass
from typing import Optional, Tuple

Point = Tuple[float, float]  # normalised 0..1 position in the (mirrored) camera image


@dataclass
class HandObservation:
    """The few landmarks we need from one camera frame."""

    index_tip: Point
    thumb_tip: Point
    wrist: Point
    middle_mcp: Point       # base of the middle finger, used to measure hand size
    aspect: float = 4 / 3   # image width / height, so distances are not stretched
    timestamp: float = 0.0


@dataclass
class GestureState:
    hand_visible: bool = False
    cursor: Optional[Point] = None   # 0..1 across the game window, or None
    pinching: bool = False
    pinch_started: bool = False
    pinch_ended: bool = False
    pinch_ratio: float = 1.0


def _distance(a: Point, b: Point, aspect: float) -> float:
    return math.hypot((a[0] - b[0]) * aspect, a[1] - b[1])


def pinch_ratio(obs: HandObservation) -> float:
    """Thumb-to-index distance divided by hand size (wrist to middle knuckle)."""
    size = _distance(obs.wrist, obs.middle_mcp, obs.aspect)
    if size < 1e-6:
        return 1.0
    return _distance(obs.thumb_tip, obs.index_tip, obs.aspect) / size


def map_to_window(point: Point, margin: float) -> Point:
    """Use the middle of the camera image for the whole window, so the edges of
    the board can be reached without stretching the hand to the image border."""
    span = 1.0 - 2.0 * margin
    x = (point[0] - margin) / span
    y = (point[1] - margin) / span
    return (min(1.0, max(0.0, x)), min(1.0, max(0.0, y)))


class GestureDetector:
    """Smooths the fingertip position and detects pinch start/end.

    The cursor is the point halfway between the thumb tip and the index fingertip.
    That point stays still while the fingers close, so the pinch does not make the
    cursor jump to another square.
    """

    def __init__(self, start_ratio: float = 0.30, release_ratio: float = 0.50,
                 smoothing: float = 0.45, lost_grace: float = 0.5,
                 margin: float = 0.12):
        self.start_ratio = start_ratio
        self.release_ratio = max(release_ratio, start_ratio)
        self.smoothing = min(1.0, max(0.05, smoothing))
        self.lost_grace = lost_grace
        self.margin = margin
        self.reset()

    def reset(self) -> None:
        self._smooth: Optional[Point] = None
        self._pinching = False
        self._last_seen: Optional[float] = None
        self._ratio = 1.0

    def update(self, obs: Optional[HandObservation], now: float) -> GestureState:
        if obs is not None:
            return self._update_visible(obs, now)
        return self._update_missing(now)

    def _update_visible(self, obs: HandObservation, now: float) -> GestureState:
        self._last_seen = now
        raw = ((obs.index_tip[0] + obs.thumb_tip[0]) / 2,
               (obs.index_tip[1] + obs.thumb_tip[1]) / 2)
        if self._smooth is None:
            self._smooth = raw
        else:
            a = self.smoothing
            self._smooth = (self._smooth[0] + a * (raw[0] - self._smooth[0]),
                            self._smooth[1] + a * (raw[1] - self._smooth[1]))
        self._ratio = pinch_ratio(obs)
        was = self._pinching
        if not was and self._ratio < self.start_ratio:
            self._pinching = True
        elif was and self._ratio > self.release_ratio:
            self._pinching = False
        return GestureState(True, map_to_window(self._smooth, self.margin),
                            self._pinching, self._pinching and not was,
                            was and not self._pinching, self._ratio)

    def _update_missing(self, now: float) -> GestureState:
        if self._last_seen is None:
            return GestureState()
        if now - self._last_seen <= self.lost_grace and self._smooth is not None:
            # Short tracking loss: keep the last cursor and pinch state.
            return GestureState(False, map_to_window(self._smooth, self.margin),
                                self._pinching, False, False, self._ratio)
        ended = self._pinching          # long loss: release the pinch safely
        self.reset()
        return GestureState(pinch_ended=ended)
