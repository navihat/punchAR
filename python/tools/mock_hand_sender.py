"""mock_hand_sender.py
- Chuan hoa dong goi ban tin UDP tuong thich nguoc voi hop dong nhom (127.0.0.1:5005).
- Chay truc tiep file nay de gia lap 2 ban tay di chuyen, nam/xoe va dam thang sang Unity.
"""
import json
import math
import socket
import time
from typing import Dict, List, Optional, Tuple

UDP_HOST = "127.0.0.1"
UDP_PORT = 5005


def flatten_landmarks_21(landmarks_21x3) -> List[float]:
    """Chuyen mang 21x3 landmarks thanh mang phang 63 so thuc lam tron 3 chu so."""
    flat: List[float] = []
    for p in landmarks_21x3:
        flat.append(round(float(p[0]), 3))
        flat.append(round(float(p[1]), 3))
        flat.append(round(float(p[2]), 3))
    return flat


def build_pose_packet(timestamp_ms: int, hands_data: List[Dict]) -> Dict:
    hands_payload = []
    for h in hands_data:
        item = {
            "hand": h["hand"],
            "x": round(float(h["x"]), 4),
            "y": round(float(h["y"]), 4),
            "shape": h.get("shape", "None"),
        }
        lms = h.get("landmarks")
        if lms is not None and len(lms) == 21:
            item["lm"] = flatten_landmarks_21(lms)
        hands_payload.append(item)

    return {
        "type": "pose",
        "t": int(timestamp_ms),
        "hands": hands_payload,
    }


def build_strike_packet(
    timestamp_ms: int, hand: str, kind: str, x: float, y: float
) -> Dict:
    return {
        "type": "strike",
        "t": int(timestamp_ms),
        "hand": hand,
        "kind": kind,  # "PUNCH_STRAIGHT" | "OPEN_PALM" | "BLOCK"
        "x": round(float(x), 4),
        "y": round(float(y), 4),
    }


def build_hand_lost_packet(timestamp_ms: int, hand: str) -> Dict:
    return {
        "type": "hand_lost",
        "t": int(timestamp_ms),
        "hand": hand,
    }


def _make_synthetic_hand_lm(curl_ratio: float) -> List[Tuple[float, float, float]]:
    lms: List[Tuple[float, float, float]] = [(0.5, 0.2, 0.0)]
    finger_x_offsets = [-0.10, -0.05, 0.0, 0.05, 0.10]
    seg_len = 0.06

    for fx in finger_x_offsets:
        base_x, base_y, base_z = 0.5 + fx, 0.35, 0.0
        lms.append((base_x, base_y, base_z))

        theta1 = curl_ratio * math.radians(75.0)
        theta2 = theta1 + curl_ratio * math.radians(85.0)
        theta3 = theta2 + curl_ratio * math.radians(65.0)

        p2 = (
            base_x,
            base_y + seg_len * math.cos(theta1),
            base_z - seg_len * math.sin(theta1),
        )
        p3 = (
            p2[0],
            p2[1] + seg_len * math.cos(theta2),
            p2[2] - seg_len * math.sin(theta2),
        )
        p4 = (
            p3[0],
            p3[1] + seg_len * math.cos(theta3),
            p3[2] - seg_len * math.sin(theta3),
        )

        lms.extend([p2, p3, p4])

    return lms


def run_mock_loop(fps: int = 30, enable_strike_demo: bool = True):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"[UDP Mock Sender] Dang phat goi tin toi {UDP_HOST}:{UDP_PORT} ({fps} FPS)...")
    print("Nhan Ctrl+C de dung.")

    interval = 1.0 / float(fps)
    start_time = time.time()
    last_strike_time = 0.0

    try:
        while True:
            t_now = time.time()
            elapsed = t_now - start_time
            now_epoch_ms = int(time.time_ns() // 1_000_000)

            left_x = 0.32 + 0.12 * math.sin(elapsed * 1.5)
            left_y = 0.50 + 0.08 * math.cos(elapsed * 2.1)

            right_x = 0.68 + 0.12 * math.cos(elapsed * 1.8)
            right_y = 0.50 + 0.08 * math.sin(elapsed * 2.3)

            curl_left = 0.5 + 0.5 * math.sin(elapsed * 2.0)
            curl_right = 0.5 + 0.5 * math.cos(elapsed * 2.0)

            shape_left = "Closed_Fist" if curl_left > 0.65 else ("Open_Palm" if curl_left < 0.35 else "None")
            shape_right = "Closed_Fist" if curl_right > 0.65 else ("Open_Palm" if curl_right < 0.35 else "None")

            hands_payload = [
                {
                    "hand": "Left",
                    "x": left_x,
                    "y": left_y,
                    "shape": shape_left,
                    "landmarks": _make_synthetic_hand_lm(curl_left),
                },
                {
                    "hand": "Right",
                    "x": right_x,
                    "y": right_y,
                    "shape": shape_right,
                    "landmarks": _make_synthetic_hand_lm(curl_right),
                },
            ]

            pose_pkt = build_pose_packet(now_epoch_ms, hands_payload)
            sock.sendto(json.dumps(pose_pkt).encode("utf-8"), (UDP_HOST, UDP_PORT))

            if enable_strike_demo and (t_now - last_strike_time) > 2.5:
                strike_hand = "Right" if int(elapsed // 2.5) % 2 == 0 else "Left"
                kind = "PUNCH_STRAIGHT"
                strike_x = right_x if strike_hand == "Right" else left_x
                strike_y = right_y if strike_hand == "Right" else left_y

                strike_pkt = build_strike_packet(now_epoch_ms, strike_hand, kind, strike_x, strike_y)
                sock.sendto(json.dumps(strike_pkt).encode("utf-8"), (UDP_HOST, UDP_PORT))
                print(f"[MOCK STRIKE] -> {strike_hand} {kind} tai ({strike_x:.2f}, {strike_y:.2f})")
                last_strike_time = t_now

            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[UDP Mock Sender] Da dung phat.")
    finally:
        sock.close()


if __name__ == "__main__":
    run_mock_loop(fps=30, enable_strike_demo=True)
