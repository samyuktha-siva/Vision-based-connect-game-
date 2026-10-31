"""Shared constants and the settings the player can change."""

from dataclasses import dataclass

APP_TITLE = "Vision-Based Gesture Connect"
WINDOW_SIZE = (1100, 720)
FPS = 60

# ---- Calm dark palette (high contrast, no bright flashing) ----
BACKGROUND = (24, 28, 46)
PANEL = (38, 44, 70)
PANEL_LIGHT = (52, 60, 92)
CELL = (46, 53, 84)
OBSTACLE = (112, 118, 140)
OBSTACLE_DARK = (80, 85, 105)
TEXT = (240, 243, 252)
TEXT_DIM = (170, 178, 205)
ACCENT = (110, 190, 255)
GOOD = (120, 225, 160)
SOFT_WARN = (255, 205, 120)
DISABLED = (80, 86, 112)

# ---- Colours: Okabe-Ito inspired so they are easier to tell apart.
# Every colour also has its own shape as an extra cue. ----
COLOR_NAMES = ["blue", "orange", "green", "pink", "red", "yellow"]
COLOR_RGB = {
    "blue": (70, 140, 255),
    "orange": (255, 160, 40),
    "green": (40, 200, 140),
    "pink": (240, 130, 200),
    "red": (235, 80, 70),
    "yellow": (250, 225, 60),
}
COLOR_SHAPES = {
    "blue": "circle",
    "orange": "square",
    "green": "triangle",
    "pink": "diamond",
    "red": "plus",
    "yellow": "star",
}

# ---- Scoring ----
PAIR_POINTS = 100  # for each newly connected pair (a pair is only scored once)

# ---- Timing choices (multiplies each level's time limit) ----
DIFFICULTIES = [("Standard time", 1.0), ("More time", 1.5), ("Lots of time", 2.5)]

# ---- Gesture tuning ----
# Pinch distance is divided by hand size, so it works near or far from the camera.
PINCH_START_RATIO = 0.30    # fingers closer than this -> pinch starts
PINCH_RELEASE_RATIO = 0.50  # fingers farther than this -> pinch ends (hysteresis)
SMOOTHING = 0.45            # 1.0 = no smoothing, smaller = smoother but slower
LOST_GRACE_SECONDS = 0.5    # keep going this long if the hand briefly disappears
ACTIVE_MARGIN = 0.12        # ignore the outer edge of the camera image
CAMERA_INDEX = 0
CAMERA_SIZE = (640, 480)


@dataclass
class Settings:
    """Options the player can change from the start screen."""

    animations: bool = True
    show_preview: bool = True
    keyboard_mode: bool = False
    difficulty_index: int = 0
    pinch_start_ratio: float = PINCH_START_RATIO
    pinch_release_ratio: float = PINCH_RELEASE_RATIO
    smoothing: float = SMOOTHING

    @property
    def difficulty_name(self) -> str:
        return DIFFICULTIES[self.difficulty_index][0]

    @property
    def time_multiplier(self) -> float:
        return DIFFICULTIES[self.difficulty_index][1]

    def cycle_difficulty(self) -> None:
        self.difficulty_index = (self.difficulty_index + 1) % len(DIFFICULTIES)
