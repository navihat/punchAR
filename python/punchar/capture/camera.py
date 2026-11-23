"""[1] Capture: background thread that keeps only the latest webcam frame."""
import threading
import time
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np


@dataclass
class Frame:
    frame_id: int
    timestamp_ms: int   # capture time, Unix epoch ms (shared clock with Unity)
    image: np.ndarray   # BGR, already mirrored if configured


class Camera:
    def __init__(self, camera=0, width=1280, height=720, fps=30, mirror=True):
        self.camera_idx = camera
        self.width = width
        self.height = height
        self.fps = fps
        self.mirror = mirror

        self.cap = self._open_capture(camera)
        # Test read 1 frame: if camera 0 fails on Windows (e.g. IR camera MSMF error -1072875772), auto-probe camera 1
        ok, _ = self.cap.read()
        if not ok and camera == 0:
            print("[Camera] Camera 0 failed to stream (likely IR sensor/Windows Hello). Auto-fallback to camera 1...")
            self.cap.release()
            self.cap = self._open_capture(1)
            self.camera_idx = 1

        self._latest: Optional[Frame] = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _open_capture(self, idx):
        cap = cv2.VideoCapture(idx)
        # MJPG before size: uncompressed YUYV caps many webcams at 10 FPS for 720p
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_FPS, self.fps)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

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
                time.sleep(0.005)
                continue
            ts = int(time.time_ns() // 1_000_000)
            if self.mirror:
                img = cv2.flip(img, 1)
            with self._lock:
                self._latest = Frame(frame_id, ts, img)
            frame_id += 1

    def read(self) -> Optional[Frame]:
        """Return the newest Frame (or None) and drop it so it isn't processed twice."""
        with self._lock:
            frame, self._latest = self._latest, None
        return frame

    def read_latest(self):
        """Non-destructive read of the latest frame: returns (ok, image, timestamp_ms)."""
        with self._lock:
            if self._latest is None:
                return False, None, 0
            return True, self._latest.image.copy(), self._latest.timestamp_ms

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)
        if self.cap and self.cap.isOpened():
            self.cap.release()

    def release(self):
        self.stop()


class LatestFrameCapture:
    """Wrapper around Camera providing (ret, frame, timestamp_ms) for interactive tools."""
    def __init__(self, src=0, width=640, height=480, fps=30):
        self._cam = Camera(camera=src, width=width, height=height, fps=fps, mirror=True).start()

    def read(self):
        return self._cam.read_latest()

    def release(self):
        self._cam.stop()

    def stop(self):
        self._cam.stop()
