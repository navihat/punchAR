"""[2] Recognizer interface and per-frame output (see docs/PROJECT_OVERVIEW.md §5)."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

Point3 = tuple[float, float, float]


@dataclass
class HandResult:
    handedness: str                 # "Left" | "Right", from the PLAYER's point of view
    shape: str                      # "Closed_Fist", "Open_Palm", "None", ...
    score: float
    landmarks: list[Point3]         # 21 points, normalized image coords
    world_landmarks: list[Point3]   # 21 points, meters


@dataclass
class FrameResult:
    frame_id: int
    timestamp_ms: int               # capture time
    hands: list[HandResult] = field(default_factory=list)


class Recognizer(ABC):
    @abstractmethod
    def load(self) -> None: ...

    @abstractmethod
    def predict(self, image, frame_id: int, timestamp_ms: int) -> FrameResult: ...

    @abstractmethod
    def close(self) -> None: ...
