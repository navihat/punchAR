"""Webcam image -> Unity as JPEG over UDP, for the AR background.

One frame per datagram: 12-byte header (little-endian int32 frame, int64 t) + JPEG bytes.
`frame` and `t` are the same as in the `pose` message of that frame, so Unity can match them.
The image is already mirrored by capture/camera.py; Unity shows it as is.

Encoding runs on its own thread, so the recognition loop only hands over the frame.
If encoding falls behind, older frames are dropped (only the latest is kept).
"""
import socket
import struct
import threading
import time

import cv2

HEADER = struct.Struct("<iq")  # frame, t
MAX_DATAGRAM = 65507


class FrameSender:
    def __init__(self, host="127.0.0.1", port=5006, width=640, height=360, quality=80, timer=None):
        self.addr = (host, port)
        self.size = (width, height)
        self.quality = quality
        self.timer = timer  # optional StageTimer: records "video_encode" and "video_bytes" (KB)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._latest = None
        self._cond = threading.Condition()
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def submit(self, image, frame_id: int, t: int):
        """Hand over a frame; returns immediately."""
        with self._cond:
            self._latest = (image, frame_id, t)
            self._cond.notify()

    def encode(self, image, frame_id: int, t: int) -> bytes | None:
        img = cv2.resize(image, self.size, interpolation=cv2.INTER_AREA)
        ok, jpg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, self.quality])
        if not ok:
            return None
        packet = HEADER.pack(frame_id, t) + jpg.tobytes()
        return packet if len(packet) <= MAX_DATAGRAM else None

    def _loop(self):
        while True:
            with self._cond:
                while self._latest is None and self._running:
                    self._cond.wait()
                if not self._running:
                    return
                item, self._latest = self._latest, None
            start = time.perf_counter()
            packet = self.encode(*item)
            if self.timer:
                self.timer.add("video_encode", (time.perf_counter() - start) * 1000)
            if packet is None:
                print(f"[FrameSender] frame {item[1]} too large for one datagram, lower quality/size")
                continue
            if self.timer:
                self.timer.add("video_kb", len(packet) / 1024)
            self.sock.sendto(packet, self.addr)

    def close(self):
        with self._cond:
            self._running = False
            self._cond.notify()
        self._thread.join(timeout=1)
        self.sock.close()
