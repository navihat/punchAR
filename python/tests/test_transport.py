"""UDP messages must match the data contract in docs/team/PHAN_CONG.vi.md."""
import json
import socket

import pytest

from punchar.decision.state_machine import StrikeEvent
from punchar.recognizer.base import FrameResult, HandResult
from punchar.transport import UdpSender


@pytest.fixture
def link():
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.bind(("127.0.0.1", 0))
    rx.settimeout(1)
    tx = UdpSender("127.0.0.1", rx.getsockname()[1])
    yield tx, lambda: json.loads(rx.recv(65535))
    tx.close()
    rx.close()


def make_hand():
    # wrist at (0.5, 0.8), middle MCP (landmark 9) at (0.5, 0.6) in MediaPipe coords (y down)
    lm = [(0.5, 0.8, 0.0)] * 21
    lm[9] = (0.5, 0.6, -0.02)
    return HandResult("Right", "Closed_Fist", 0.93, lm, [(0.0, 0.0, 0.0)] * 21)


def test_pose(link):
    tx, recv = link
    tx.send_pose(FrameResult(42, 1795072926644, [make_hand()]))
    msg = recv()
    assert msg["type"] == "pose" and msg["t"] == 1795072926644 and msg["frame"] == 42
    (h,) = msg["hands"]
    assert h["hand"] == "Right" and h["shape"] == "Closed_Fist" and h["score"] == 0.93
    assert (h["x"], h["y"]) == (0.5, 0.4)          # y flipped to Unity viewport (up)
    assert h["size"] == 0.2
    assert len(h["lm"]) == 63
    assert h["lm"][27:30] == [0.5, 0.4, -0.02]     # landmark 9, flat [x, y, z]


def test_pose_without_hands(link):
    tx, recv = link
    tx.send_pose(FrameResult(1, 1, []))
    assert recv()["hands"] == []


def test_strike(link):
    tx, recv = link
    tx.send_strike(StrikeEvent(5, "Left", "PUNCH_STRAIGHT", 0.31, 0.25))
    assert recv() == {"type": "strike", "t": 5, "hand": "Left", "kind": "PUNCH_STRAIGHT", "x": 0.31, "y": 0.75}


def test_hand_lost(link):
    tx, recv = link
    tx.send_hand_lost(7, "Right")
    assert recv() == {"type": "hand_lost", "t": 7, "hand": "Right"}


def test_video_frame():
    import cv2
    import numpy as np

    from punchar.transport import FrameSender
    from punchar.transport.frame_sender import HEADER

    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.bind(("127.0.0.1", 0))
    rx.settimeout(1)
    tx = FrameSender("127.0.0.1", rx.getsockname()[1], width=640, height=360, quality=80)
    img = np.zeros((720, 1280, 3), np.uint8)
    img[:, :640] = (0, 0, 255)  # left half red (BGR): checks the image is not flipped again
    tx.submit(img, 7, 1795072926644)
    packet = rx.recv(65535)
    tx.close()
    rx.close()

    assert HEADER.unpack_from(packet) == (7, 1795072926644)
    out = cv2.imdecode(np.frombuffer(packet[HEADER.size:], np.uint8), cv2.IMREAD_COLOR)
    assert out.shape == (360, 640, 3)
    assert out[180, 100, 2] > 200 and out[180, 540, 2] < 50
