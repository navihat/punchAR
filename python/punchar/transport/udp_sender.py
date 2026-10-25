"""Python -> Unity JSON messages over UDP. The message format is a contract (docs §5)."""
import json
import socket

from punchar.decision.state_machine import StrikeEvent
from punchar.recognizer.base import FrameResult


class UdpSender:
    def __init__(self, host="127.0.0.1", port=5005):
        self.addr = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def _send(self, msg: dict):
        self.sock.sendto(json.dumps(msg, separators=(",", ":")).encode(), self.addr)

    def send_pose(self, frame: FrameResult):
        hands = []
        for h in frame.hands:
            # palm center ~ middle-finger MCP
            x, y, _ = h.landmarks[9]
            hands.append({"hand": h.handedness, "x": round(x, 4), "y": round(y, 4), "shape": h.shape})
        self._send({"type": "pose", "t": frame.timestamp_ms, "hands": hands})

    def send_strike(self, ev: StrikeEvent):
        self._send({"type": "strike", "t": ev.t, "hand": ev.hand, "kind": ev.kind,
                    "x": round(ev.x, 4), "y": round(ev.y, 4)})

    def send_hand_lost(self, t: int, hand: str):
        self._send({"type": "hand_lost", "t": t, "hand": hand})

    def close(self):
        self.sock.close()
