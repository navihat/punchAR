"""Plays back recorded FrameResult sequences (JSONL) for tests and game dev without a webcam."""
import json
from pathlib import Path

from punchar.recognizer.base import FrameResult, HandResult, Recognizer


class ReplayRecognizer(Recognizer):
    def __init__(self, path: Path):
        self.path = Path(path)
        self._frames = []
        self._idx = 0

    def load(self):
        with open(self.path) as f:
            for line in f:
                d = json.loads(line)
                hands = [HandResult(**h) for h in d.pop("hands", [])]
                self._frames.append(FrameResult(hands=hands, **d))

    def predict(self, image=None, frame_id=None, timestamp_ms=None):
        """Ignore inputs and return the next recorded frame (None when finished)."""
        if self._idx >= len(self._frames):
            return None
        frame = self._frames[self._idx]
        self._idx += 1
        return frame

    def close(self):
        self._frames.clear()
