"""
mock_udp_streamer.py
--------------------
Phát luồng dữ liệu giả lập UDP (Port 5005) để kiểm thử bàn tay 3D trong Unity
ngay cả khi không có webcam hoặc muốn kiểm tra độ mượt/hệ trục uốn.

Cách dùng:
  python python/tools/mock_udp_streamer.py
"""
import math
import socket
import time
import json

HOST = "127.0.0.1"
PORT = 5005
FPS = 60

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
print(f"[MockUdpStreamer] Đang phát gói tin UDP tới {HOST}:{PORT} ở tần số {FPS} FPS...")
print("Mở scene Sandbox_Duy.unity trong Unity Editor và bấm PLAY để quan sát.")
print("Nhấn Ctrl+C để dừng.")

t0 = time.time()
frame_id = 0

try:
    while True:
        now = time.time()
        elapsed = now - t0
        frame_id += 1
        t_ms = int(now * 1000)

        # Tạo chu kỳ co duỗi ngón tay và di chuyển nhẹ nhàng
        cycle = math.sin(elapsed * 2.0)  # -1 .. +1
        curl_ratio = (cycle + 1.0) * 0.5  # 0.0 (xòe) .. 1.0 (nắm)
        shape = "Closed_Fist" if curl_ratio > 0.7 else "Open_Palm"

        # Tọa độ di chuyển nhẹ
        x_left = 0.35 + 0.05 * math.sin(elapsed * 1.5)
        y_left = 0.50 + 0.05 * math.cos(elapsed * 1.5)
        x_right = 0.65 - 0.05 * math.sin(elapsed * 1.5)
        y_right = 0.50 + 0.05 * math.cos(elapsed * 1.5)

        # Tạo 21 landmarks cho mỗi tay
        def make_landmarks(cx, cy, is_left, curl):
            # Điểm gốc cổ tay
            p0 = [cx, cy - 0.12, 0.0]
            lms = [p0]
            sign = -1 if is_left else 1

            # Ngón cái (1..4)
            for j in range(1, 5):
                spread = 0.03 * j
                curl_offset = curl * 0.04 * (j / 4.0)
                lms.append([cx + sign * (0.02 + spread * 0.5), cy - 0.08 + spread * 0.4 - curl_offset, -curl_offset])

            # 4 ngón dài: Index (5..8), Middle (9..12), Ring (13..16), Pinky (17..20)
            finger_xs = [-0.04, -0.01, 0.02, 0.05]
            if not is_left:
                finger_xs = [0.04, 0.01, -0.02, -0.05]

            for f_idx, fx in enumerate(finger_xs):
                mcp_y = cy - 0.02
                for seg in range(1, 5):
                    seg_len = 0.03 * seg
                    bend_y = -curl * 0.05 * (seg / 4.0)
                    bend_z = -curl * 0.06 * (seg / 4.0)
                    lms.append([cx + fx, mcp_y + seg_len + bend_y, bend_z])

            # Flatten to 63 floats
            flat = []
            for p in lms:
                flat += [round(p[0], 4), round(p[1], 4), round(p[2], 4)]
            return flat

        left_lm = make_landmarks(x_left, y_left, True, curl_ratio)
        right_lm = make_landmarks(x_right, y_right, False, curl_ratio)

        pose_msg = {
            "type": "pose",
            "t": t_ms,
            "frame": frame_id,
            "hands": [
                {
                    "hand": "Left",
                    "x": round(x_left, 4),
                    "y": round(y_left, 4),
                    "size": 0.15,
                    "shape": shape,
                    "score": 0.95,
                    "lm": left_lm
                },
                {
                    "hand": "Right",
                    "x": round(x_right, 4),
                    "y": round(y_right, 4),
                    "size": 0.15,
                    "shape": shape,
                    "score": 0.95,
                    "lm": right_lm
                }
            ]
        }

        data = json.dumps(pose_msg, separators=(",", ":")).encode("utf-8")
        sock.sendto(data, (HOST, PORT))
        time.sleep(1.0 / FPS)
except KeyboardInterrupt:
    print("\n[MockUdpStreamer] Đã dừng phát.")
finally:
    sock.close()
