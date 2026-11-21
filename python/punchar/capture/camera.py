"""[1] Capture: background thread that keeps only the latest webcam frame."""
import threading
import time
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class Frame:
    frame_id: int
    timestamp_ms: int   # capture time in Unix epoch ms
    image: np.ndarray   # BGR, already mirrored if configured


class Camera:
    def __init__(self, camera=0, width=1280, height=720, fps=30, mirror=True):
        self.cap = cv2.VideoCapture(camera)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
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
            ts = int(time.time_ns() // 1_000_000)
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
        if self.cap and self.cap.isOpened():
            self.cap.release()


class LatestFrameCapture:
    """Dedicated background thread capture used by interactive inspection tools."""
    def __init__(self, src=0, width=640, height=480, fps=30):
        self.src = src
        self.cap = cv2.VideoCapture(src)
        if not self.cap.isOpened():
            raise RuntimeError(
                f"[!] Cannot open webcam with src={src}. "
                f"Please check camera connection or try src=1, 2."
            )
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.lock = threading.Lock()
        self.latest_frame = None
        self.timestamp_ms = 0
        self.running = True
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()

    def _update(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                flipped = cv2.flip(frame, 1)
                ts = int(time.time_ns() // 1_000_000)
                with self.lock:
                    self.latest_frame = flipped
                    self.timestamp_ms = ts
            else:
                time.sleep(0.005)

    def read(self):
        with self.lock:
            if self.latest_frame is None:
                return False, None, 0
            return True, self.latest_frame.copy(), self.timestamp_ms

    def release(self):
        self.running = False
        if hasattr(self, 'thread') and self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if hasattr(self, 'cap') and self.cap and self.cap.isOpened():
            self.cap.release()
