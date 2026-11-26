"""[3] Decision logic: per-hand state machine IDLE -> WINDUP -> STRIKE -> COOLDOWN -> IDLE.

All temporal rules live here; thresholds come from config [decision], times in ms.
Active gestures: PUNCH_STRAIGHT, BLOCK, OPEN_PALM.
"""
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Dict, List, Optional, Tuple

from punchar.recognizer.base import FrameResult, HandResult


class HandState(Enum):
    IDLE = "IDLE"
    WINDUP = "WINDUP"
    STRIKE = "STRIKE"
    COOLDOWN = "COOLDOWN"
    BLOCK_READY = "BLOCK_READY"


@dataclass
class StrikeEvent:
    t: int          # capture timestamp of the source frame
    hand: str       # "Left" | "Right"
    kind: str       # PUNCH_STRAIGHT | BLOCK | OPEN_PALM
    x: float
    y: float


@dataclass
class _HandTrack:
    state: HandState = HandState.IDLE
    state_since_ms: int = 0
    last_seen_ms: int = 0
    cooldown_until_ms: int = 0
    history: deque = field(default_factory=deque)  # (t_ms, x, y, size)
    last_valid_fist_ms: int = -9999
    last_valid_palm_ms: int = -9999
    is_block_ready: bool = False
    block_start_ms: int = -1
    is_reported_lost: bool = True


def hand_size(hand: HandResult) -> float:
    """Wrist-to-middle-MCP distance in normalized image coords; grows as the fist approaches."""
    if not hand.landmarks or len(hand.landmarks) < 10:
        return 0.1
    (x0, y0, _), (x1, y1, _) = hand.landmarks[0], hand.landmarks[9]
    return ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5


class DecisionLogic:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.tracks: Dict[str, _HandTrack] = {"Left": _HandTrack(), "Right": _HandTrack()}
        self.lost_hands: List[str] = []

        # Temporal thresholds (all in ms)
        self.window_ms = cfg.get("window_ms", cfg.get("punch_window_ms", 120))
        self.punch_window_ms = cfg.get("punch_window_ms", 150)
        self.cooldown_ms = cfg.get("cooldown_ms", 250)
        self.block_hold_ms = cfg.get("block_hold_ms", 120)
        self.blur_grace_ms = cfg.get("blur_grace_ms", 60)
        self.lost_grace_ms = cfg.get("lost_grace_ms", 300)

        # Kinematic & confidence thresholds
        self.min_shape_score = cfg.get("min_shape_score", 0.60)
        self.punch_size_growth = cfg.get("punch_size_growth", 0.15)
        self.punch_min_vel_scale = cfg.get("punch_min_vel_scale", 1.30)
        self.palm_min_scale_gain = cfg.get("palm_min_scale_gain", 0.12)
        self.palm_min_vel_scale = cfg.get("palm_min_vel_scale", 0.90)
        self.block_max_planar_vel = cfg.get("block_max_planar_vel", 0.85)
        self.block_max_scale_vel = cfg.get("block_max_scale_vel", 0.65)

    def _compute_kinematics(self, track: _HandTrack, x: float, y: float, s: float, t_ms: int) -> Tuple[float, float, float]:
        track.history.append((t_ms, x, y, s))
        while len(track.history) > 1 and (t_ms - track.history[0][0]) > self.punch_window_ms:
            track.history.popleft()

        v_scale, scale_gain, v_planar = 0.0, 0.0, 0.0
        if len(track.history) >= 2:
            t0, x0, y0, s0 = track.history[0]
            dt_sec = max((t_ms - t0) / 1000.0, 1e-4)
            if dt_sec >= 0.02:
                scale_gain = (s - s0) / max(s0, 1e-4)
                v_scale = scale_gain / dt_sec
                v_planar = math.hypot(x - x0, y - y0) / (max(s, 0.05) * dt_sec)
        return v_scale, scale_gain, v_planar

    def update(self, frame: FrameResult) -> List[StrikeEvent]:
        """Feed one frame, return strike events confirmed on this frame."""
        events: List[StrikeEvent] = []
        self.lost_hands = []
        t_ms = frame.timestamp_ms
        seen_hands = set()

        for hand in frame.hands:
            side = hand.handedness
            track = self.tracks.get(side)
            if track is None:
                continue

            seen_hands.add(side)
            track.last_seen_ms = t_ms
            track.is_reported_lost = False

            # Palm position
            if hand.landmarks and len(hand.landmarks) > 9:
                x, y, _ = hand.landmarks[9]
            else:
                x, y = 0.5, 0.5
            s = hand_size(hand)

            v_scale, scale_gain, v_planar = self._compute_kinematics(track, x, y, s, t_ms)

            # Check cooldown
            if t_ms < track.cooldown_until_ms:
                track.state = HandState.COOLDOWN
                continue

            # Check shape classifications
            is_fist = (hand.shape == "Closed_Fist" and hand.score >= self.min_shape_score)
            is_palm = (hand.shape == "Open_Palm" and hand.score >= self.min_shape_score)

            if is_fist:
                track.last_valid_fist_ms = t_ms
            if is_palm:
                track.last_valid_palm_ms = t_ms

            fist_ready = is_fist or ((t_ms - track.last_valid_fist_ms) <= self.blur_grace_ms)
            palm_ready = is_palm or ((t_ms - track.last_valid_palm_ms) <= self.blur_grace_ms)

            # 1. PUNCH_STRAIGHT
            if fist_ready:
                req_growth = self.punch_size_growth
                req_vel = self.punch_min_vel_scale
                if scale_gain >= req_growth or v_scale >= req_vel:
                    track.state = HandState.STRIKE
                    track.cooldown_until_ms = t_ms + self.cooldown_ms
                    track.history.clear()
                    events.append(StrikeEvent(t=t_ms, hand=side, kind="PUNCH_STRAIGHT", x=round(x, 4), y=round(y, 4)))
                    continue
                elif scale_gain >= 0.5 * req_growth or v_scale >= 0.5 * req_vel:
                    track.state = HandState.WINDUP

            # 2. OPEN_PALM
            if palm_ready:
                req_growth = self.palm_min_scale_gain
                req_vel = self.palm_min_vel_scale
                if scale_gain >= req_growth or v_scale >= req_vel:
                    track.state = HandState.STRIKE
                    track.cooldown_until_ms = t_ms + self.cooldown_ms
                    track.history.clear()
                    events.append(StrikeEvent(t=t_ms, hand=side, kind="OPEN_PALM", x=round(x, 4), y=round(y, 4)))
                    continue

            # 3. BLOCK (check stationary fist)
            if fist_ready and v_planar <= self.block_max_planar_vel and abs(v_scale) <= self.block_max_scale_vel:
                if not track.is_block_ready:
                    track.is_block_ready = True
                    track.block_start_ms = t_ms
                track.state = HandState.BLOCK_READY
            else:
                track.is_block_ready = False
                track.block_start_ms = -1
                if track.state != HandState.WINDUP:
                    track.state = HandState.IDLE

        # Check BLOCK hold duration
        for side, track in self.tracks.items():
            if side in seen_hands and track.is_block_ready and track.block_start_ms >= 0:
                if (t_ms - track.block_start_ms) >= self.block_hold_ms and t_ms >= track.cooldown_until_ms:
                    track.state = HandState.STRIKE
                    track.cooldown_until_ms = t_ms + self.cooldown_ms
                    track.is_block_ready = False
                    track.block_start_ms = -1
                    last_pos = track.history[-1] if track.history else (t_ms, 0.5, 0.5, 0.1)
                    events.append(StrikeEvent(t=t_ms, hand=side, kind="BLOCK", x=round(last_pos[1], 4), y=round(last_pos[2], 4)))

        # Handle hand tracking loss
        for side, track in self.tracks.items():
            if side not in seen_hands:
                if (t_ms - track.last_seen_ms) > self.lost_grace_ms:
                    if not track.is_reported_lost and track.last_seen_ms > 0:
                        track.is_reported_lost = True
                        self.lost_hands.append(side)
                    track.state = HandState.IDLE
                    track.history.clear()
                    track.is_block_ready = False

        return events
