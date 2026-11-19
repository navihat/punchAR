"""Python -> Unity JSON messages over UDP.

The message format is a contract: docs/team/PHAN_CONG.vi.md, "Hợp đồng dữ liệu Python → Unity".
Coordinates are converted here (and only here) from MediaPipe's y-down to Unity's viewport y-up.
"""
import json
import socket

from punchar.decision.state_machine import StrikeEvent, hand_size
from punchar.recognizer.base import FrameResult

PALM = 9  # middle-finger MCP, used as the hand position


def _r(v: float) -> float:
    return round(v, 4)


class UdpSender:
    def __init__(self, host="127.0.0.1", port=5005):
        self.addr = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def _send(self, msg: dict):
        self.sock.sendto(json.dumps(msg, separators=(",", ":")).encode(), self.addr)

    def send_pose(self, frame: FrameResult):
        hands = []
        for h in frame.hands:
            x, y, _ = h.landmarks[PALM]
            lm = []
            for px, py, pz in h.landmarks:
                lm += [_r(px), _r(1 - py), _r(pz)]
            hands.append({"hand": h.handedness, "x": _r(x), "y": _r(1 - y), "size": _r(hand_size(h)),
                          "shape": h.shape, "score": _r(h.score), "lm": lm})
        self._send({"type": "pose", "t": frame.timestamp_ms, "frame": frame.frame_id, "hands": hands})

    def send_strike(self, ev: StrikeEvent):
        self._send({"type": "strike", "t": ev.t, "hand": ev.hand, "kind": ev.kind,
                    "x": _r(ev.x), "y": _r(1 - ev.y)})

    def send_hand_lost(self, t: int, hand: str):
        self._send({"type": "hand_lost", "t": t, "hand": hand})

    def close(self):
        self.sock.close()
