"""[1] Capture: background thread that keeps only the latest webcam frame."""
import threading
import time
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class Frame:
    frame_id: int
    timestamp_ms: int   # capture time, time.monotonic based
    image: np.ndarray   # BGR, already mirrored if configured


class Camera:
    def __init__(self, camera=0, width=1280, height=720, fps=30, mirror=True):
        self.cap = cv2.VideoCapture(camera)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera {camera}")
        self.mirror = mirror
        self._latest = None
        self._lock = threading.Lock()
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def _loop(self):
        frame_id = 0
        while self._running:
            ok, img = self.cap.read()
            if not ok:
                continue
            ts = int(time.monotonic() * 1000)
            if self.mirror:
                img = cv2.flip(img, 1)
            with self._lock:
                self._latest = Frame(frame_id, ts, img)
            frame_id += 1

    def read(self):
        """Return the newest Frame (or None) and drop it so it isn't processed twice."""
        with self._lock:
            frame, self._latest = self._latest, None
        return frame

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)
        self.cap.release()
