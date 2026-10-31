"""Webcam capture (OpenCV) and hand landmarks (MediaPipe) in a background thread.

Nothing here is imported by the game logic or the tests, and cv2/mediapipe are only
imported when the camera is started, so the rest of the project works without them.
"""

import sys
import threading
import time
from typing import Optional, Tuple

from vision.gesture_detector import HandObservation

# MediaPipe hand landmark numbers
WRIST, THUMB_TIP, INDEX_TIP, MIDDLE_MCP = 0, 4, 8, 9
MAX_FAILED_READS = 30   # about one second of failed frames = camera lost


def observation_from_landmarks(landmarks, aspect: float, timestamp: float) -> HandObservation:
    """Build a HandObservation from a list of landmarks that have .x and .y."""
    def point(i):
        return (float(landmarks[i].x), float(landmarks[i].y))
    return HandObservation(index_tip=point(INDEX_TIP), thumb_tip=point(THUMB_TIP),
                           wrist=point(WRIST), middle_mcp=point(MIDDLE_MCP),
                           aspect=aspect, timestamp=timestamp)


class HandTracker:
    """Reads the webcam in a background thread so the game window never freezes.

    status: "stopped", "starting", "running" or "error" (see error_message).
    """

    def __init__(self, camera_index: int = 0, size: Tuple[int, int] = (640, 480),
                 preview_size: Tuple[int, int] = (160, 120)):
        self.camera_index = camera_index
        self.size = size
        self.preview_size = preview_size
        self.status = "stopped"
        self.error_message = ""
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._observation: Optional[HandObservation] = None
        self._preview: Optional[bytes] = None

    # ---------------------------------------------------------- control
    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self.status = "starting"
        self.error_message = ""
        self._observation = None
        self._preview = None
        self._thread = threading.Thread(target=self._run, name="hand-tracker", daemon=True)
        self._thread.start()

    def retry(self) -> None:
        """Stop everything and try to open the camera again."""
        self.stop()
        self.start()

    def stop(self) -> None:
        """Release the webcam. Safe to call more than once."""
        self._stop.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=3.0)
        self._thread = None
        if self.status != "error":
            self.status = "stopped"

    # ----------------------------------------------------------- results
    def latest(self) -> Optional[HandObservation]:
        with self._lock:
            return self._observation

    def preview(self) -> Optional[Tuple[bytes, Tuple[int, int]]]:
        """Small RGB image of the camera for the on-screen preview."""
        with self._lock:
            if self._preview is None:
                return None
            return self._preview, self.preview_size

    def _fail(self, message: str) -> None:
        self.error_message = message
        self.status = "error"

    # ------------------------------------------------------------ thread
    def _open_camera(self, cv2):
        backends = [cv2.CAP_DSHOW, None] if sys.platform == "win32" else [None]
        for backend in backends:
            cap = (cv2.VideoCapture(self.camera_index, backend) if backend is not None
                   else cv2.VideoCapture(self.camera_index))
            if cap is not None and cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.size[0])
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.size[1])
                return cap
            if cap is not None:
                cap.release()
        return None

    def _run(self) -> None:
        cap = None
        hands = None
        try:
            try:
                import cv2
                import mediapipe as mp
            except ImportError as err:
                self._fail(f"A required library is missing ({err.name}). "
                           "Run: python -m pip install -r requirements.txt")
                return
            if not hasattr(mp, "solutions"):
                self._fail("This MediaPipe version is not supported. "
                           "Install the version in requirements.txt.")
                return
            cap = self._open_camera(cv2)
            if cap is None:
                self._fail("The webcam could not be opened. Check that it is plugged in, "
                           "not used by another app, and that camera access is allowed.")
                return
            hands = mp.solutions.hands.Hands(
                max_num_hands=1, model_complexity=0,
                min_detection_confidence=0.6, min_tracking_confidence=0.5)
            self.status = "running"
            failed = 0
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    failed += 1
                    if failed >= MAX_FAILED_READS:
                        self._fail("The webcam stopped sending pictures. "
                                   "It may have been unplugged.")
                        return
                    time.sleep(0.03)
                    continue
                failed = 0
                frame = cv2.flip(frame, 1)       # mirror: moving right looks like moving right
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                height, width = rgb.shape[:2]
                result = hands.process(rgb)
                obs = None
                if result.multi_hand_landmarks:
                    obs = observation_from_landmarks(
                        result.multi_hand_landmarks[0].landmark,
                        width / float(height), time.monotonic())
                small = cv2.resize(rgb, self.preview_size)
                with self._lock:
                    self._observation = obs
                    self._preview = small.tobytes()
        except Exception as err:  # keep the game alive whatever the camera does
            self._fail(f"Webcam problem: {err}")
        finally:
            try:
                if hands is not None:
                    hands.close()
            finally:
                if cap is not None:
                    cap.release()
            with self._lock:
                self._observation = None
