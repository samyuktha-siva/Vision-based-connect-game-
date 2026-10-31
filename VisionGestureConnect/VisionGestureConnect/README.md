# Vision-Based Gesture Connect Game

A calm, colourful puzzle game played with your **hand in front of a webcam**.
Pinch your thumb and finger over a coloured dot, move to the dot with the same colour,
and let go. Ten levels. Built with Python, Pygame, OpenCV and MediaPipe.

It was designed to be gentle and predictable for autistic children: clear short
instructions, buttons that never move, encouraging words, no flashing, no sounds,
extra time options, and a switch to turn animations off. Every child is different,
so please adjust the options (start screen) to suit the player.

## Run it on Windows (PowerShell)

Use **Python 3.10, 3.11 or 3.12 (64-bit)**. MediaPipe does not support 3.13 yet.

```powershell
cd VisionGestureConnect
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run the tests (no webcam needed):

```powershell
python -m pytest -q
```

Play:

```powershell
python main.py
```

## How to play

1. **Start Game** (or pick a level number). Allow the camera if Windows asks.
2. Hold your hand up so the camera can see it. A ring follows your hand.
3. **Pinch** (thumb tip touches finger tip) while the ring is over a dot.
4. Keep pinching and **move** to the matching dot. The line follows you.
5. **Let go** to finish. If you let go too early the line just disappears. Try again!
6. Connect every pair to win. The timer only starts at your first pinch.

You can also pinch over any on-screen button to press it. Mouse clicks on buttons work
for a helper adult, but the puzzle itself is only played with gestures.

| Button / key | What it does |
|---|---|
| Pause / Resume (P or Esc) | Stops and restarts the timer |
| Restart (R) | Starts the level again: clears lines, score and timer |
| Next Level (N or Enter) | Only after winning |
| Exit | Releases the webcam and closes the game |

**Optional settings (start screen):** time (Standard, More time, Lots of time),
animations on/off, camera preview on/off, keyboard test mode.

### Keyboard test mode (not webcam play)

For testing without a camera: turn on *Keyboard test mode* (or choose it on the camera
error screen). Arrow keys move, **Space** pinches (press once to grab, again to release).
The screen always says it is a test mode.

## The rules

* Only dots of the **same colour** connect. Each colour also has its own **shape**
  (circle, square, triangle, diamond, plus, star) as an extra clue.
* A line can only start on a dot, and moves up, down, left or right (no diagonals).
* Lines cannot enter **grey blocked squares**, leave the board, cross another line,
  or pass over any dot.
* The path is built one square at a time, so moving fast never jumps over a block.
* Moving back along your own line shortens it.
* A pair scores 100 points **once**, even if you redraw it. Finishing also adds 1 point
  per second left.
* A level is won when **all pairs** are connected.
* Winning unlocks the next level. Progress is saved in `progress.json`.
* When time runs out you see: "Great effort! Every try helps you learn. Would you like
  to try again?" and can Restart or Exit.

The path check is a simple walk along the path (see `validate_path` in `game/board.py`).

## Levels

Ten levels are defined as data in `game/level_manager.py` (grid size, pairs, blocked
squares, time, seed). Each level is built from its seed, so it is the same every time.
The builder draws a valid solution first and puts the dots at the ends, so **every level
is solvable**. Levels grow from a 5x5 grid with 3 pairs and no obstacles to an 8x8 grid
with 6 pairs and 16 blocked squares.

## Project layout

```
main.py                 the game loop and screens
game/board.py           grid, level data, path validation
game/game_logic.py      rules, score, timer (no Pygame)
game/level_manager.py   ten levels, unlocking
game/ui.py, effects.py  drawing and gentle animations
game/settings.py        colours, timing and gesture settings
vision/hand_tracker.py  webcam + MediaPipe in a background thread
vision/gesture_detector.py  smoothing, pinch detection (no camera needed to test)
tests/                  automated tests
```

## Troubleshooting

**"python" or "py" is not recognized.** Install Python from python.org and tick
"Add python.exe to PATH". Then open a new PowerShell window.

**PowerShell blocks `Activate.ps1`.** Run this once, then activate again:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

**MediaPipe will not install.** Check `python --version` is 3.10, 3.11 or 3.12 and 64-bit.
If you have several versions, make the environment with one of them, e.g.
`py -3.12 -m venv .venv`. Update pip and try again. A very new Python (3.13+) will fail.

**The webcam cannot be opened.** Close apps that use the camera (Zoom, Teams, browser
tabs). In Windows go to Settings > Privacy & security > Camera and allow desktop apps.
Then press *Try camera again* in the game. With two cameras, change `CAMERA_INDEX` in
`game/settings.py` to `1`.

**Pinching is too hard or too easy.** Change `PINCH_START_RATIO` (smaller = pinch must
be tighter) and `PINCH_RELEASE_RATIO` in `game/settings.py`. Good, even light helps.
If the cursor shakes, lower `SMOOTHING` (for example `0.3`).

## Test results and honest limitations

Checked in a Linux sandbox with Python 3.12, pygame 2.6.1, mediapipe 0.10.21,
opencv-contrib 4.11, numpy 1.26.4:

* `python -m pytest -q` : **89 passed** (rules, scoring, duplicate pairs, invalid paths,
  obstacles, all ten levels solvable and playable, unlocking, restart, timer pause and
  resume, gesture logic with made-up hand data).
* The whole game was driven headless (menu, game, win, pause, time-up, camera error and
  final screens) without errors, and screenshots were inspected.
* With no webcam present, the camera error path and retry worked, and MediaPipe loaded
  and ran on a blank picture.

**Not tested:** a real webcam, real hand tracking, and real pinch gestures (no camera was
available). The pinch thresholds are sensible starting values and may need tuning.
Installation on Windows was not tested either. The game has not been tried with children,
so the accessibility choices are based on common guidance, not on testing with users.
The game has no sound.
