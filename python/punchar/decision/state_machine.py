"""[3] Decision logic: per-hand state machine IDLE -> WINDUP -> STRIKE -> COOLDOWN -> IDLE.

All temporal rules live here; thresholds come from config [decision], times in ms.
"""
from dataclasses import dataclass
from enum import Enum

from punchar.recognizer.base import FrameResult, HandResult


class HandState(Enum):
    IDLE = "IDLE"
    WINDUP = "WINDUP"
    STRIKE = "STRIKE"
    COOLDOWN = "COOLDOWN"


@dataclass
class StrikeEvent:
    t: int          # capture timestamp of the source frame
    hand: str       # "Left" | "Right"
    kind: str       # PUNCH_STRAIGHT | BLOCK | OPEN_PALM | HOOK
    x: float
    y: float


@dataclass
class _HandTrack:
    state: HandState = HandState.IDLE
    state_since_ms: int = 0
    last_seen_ms: int = 0
    # TODO: history of (t, hand_size, x, y) for velocity / size-growth checks


def hand_size(hand: HandResult) -> float:
    """Wrist-to-middle-MCP distance in normalized image coords; grows as the fist approaches."""
    (x0, y0, _), (x1, y1, _) = hand.landmarks[0], hand.landmarks[9]
    return ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5


class DecisionLogic:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.tracks = {"Left": _HandTrack(), "Right": _HandTrack()}

    def update(self, frame: FrameResult) -> list[StrikeEvent]:
        """Feed one frame, return strike events confirmed on this frame."""
        events = []
        for hand in frame.hands:
            track = self.tracks.get(hand.handedness)
            if track is None:
                continue
            track.last_seen_ms = frame.timestamp_ms
            # TODO: implement transitions
            #   IDLE -> WINDUP: fist with score >= min_shape_score
            #   WINDUP -> STRIKE: hand_size grows by punch_size_growth within punch_window_ms
            #   STRIKE -> COOLDOWN: emit StrikeEvent
            #   COOLDOWN -> IDLE: after cooldown_ms
            # TODO [TBD]: BLOCK pose, OPEN_PALM meaning, optional HOOK
        # TODO: hands missing longer than lost_grace_ms -> reset + hand_lost
        return events
