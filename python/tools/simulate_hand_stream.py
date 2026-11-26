"""
simulate_hand_stream.py
-----------------------
Công cụ giả lập luồng dữ liệu UDP (Port 5005) gửi tới Unity:
Phát tuần tự chuỗi 5 pha kiểm thử cử chỉ và sự kiện:
  1. Xòe tay (OPEN_PALM) -> Phát sự kiện strike "OPEN_PALM" (tay Left)
  2. Nắm đấm (CLOSED_FIST) -> Co gập 15 đốt ngón tay mượt mà
  3. Đấm thẳng (PUNCH_STRAIGHT) -> Lao nắm đấm (Lunge) + Phát strike "PUNCH_STRAIGHT" (tay Right)
  4. Đấm thủ / Phòng thủ (BLOCK) -> Khép tay chắn ngực + Phát strike "BLOCK" (tay Left)
  5. Mất tay (HAND_LOST) -> Rời tay Left khỏi khung hình, phát gói tin "hand_lost"

Tuân thủ 100% hợp đồng dữ liệu UDP giữa Python và Unity (docs/team/PHAN_CONG.vi.md).

Cách chạy:
  python python/tools/simulate_hand_stream.py
"""

import json
import math
import socket
import sys
import time

HOST = "127.0.0.1"
PORT = 5005
FPS = 60
CYCLE_DURATION = 15.0  # Mỗi chu kỳ 15 giây (3s mỗi pha x 5 pha)

PHASES = [
    ("1. XÒE BÀN TAY (OPEN_PALM)", 0.0, 3.0),
    ("2. NẮM ĐẤM (CLOSED_FIST)", 3.0, 6.0),
    ("3. ĐẤM THẲNG (PUNCH_STRAIGHT)", 6.0, 9.0),
    ("4. ĐẤM THỦ / PHÒNG THỦ (BLOCK)", 9.0, 12.0),
    ("5. THỬ NGHIỆM MẤT TAY (HAND_LOST)", 12.0, 15.0),
]


def make_landmarks(cx, cy, cz, is_left, curl_ratio):
    """
    Sinh 21 điểm landmarks (MediaPipe) chuẩn hóa [0..1] x, y và z relative:
    0: Wrist
    1..4: Thumb (CMC, MCP, IP, Tip)
    5..8: Index (MCP, PIP, DIP, Tip)
    9..12: Middle (MCP, PIP, DIP, Tip)
    13..16: Ring (MCP, PIP, DIP, Tip)
    17..20: Pinky (MCP, PIP, DIP, Tip)
    """
    sign = -1.0 if is_left else 1.0
    lms = []

    # 0. Cổ tay (Wrist)
    p0 = [cx, cy - 0.12, cz]
    lms.append(p0)

    # 1..4. Ngón cái
    for j in range(1, 5):
        spread_x = sign * (0.02 + 0.025 * j)
        spread_y = 0.02 * j
        curl_x = sign * (curl_ratio * 0.035 * (j / 4.0))  # Khép vào lòng bàn tay
        curl_z = -curl_ratio * 0.045 * (j / 4.0)          # Ôm lên mặt trước nắm đấm
        lms.append([cx + spread_x - curl_x, cy - 0.09 + spread_y, cz + curl_z])

    # 4 ngón dài: Index (5..8), Middle (9..12), Ring (13..16), Pinky (17..20)
    finger_offsets_x = [-0.045, -0.015, 0.015, 0.045]
    if not is_left:
        finger_offsets_x = [0.045, 0.015, -0.015, -0.045]

    for f_idx, fx in enumerate(finger_offsets_x):
        mcp_y = cy - 0.02
        for seg in range(1, 5):
            seg_len = 0.032 * seg
            bend_y = -curl_ratio * 0.055 * (seg / 4.0)
            bend_z = -curl_ratio * 0.070 * (seg / 4.0)
            lms.append([cx + fx, mcp_y + seg_len + bend_y, cz + bend_z])

    # Flatten to 63 floats
    flat = []
    for p in lms:
        flat += [round(p[0], 4), round(p[1], 4), round(p[2], 4)]
    return flat


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print("=" * 80)
    print(f"[SimulateHandStream] Đang phát gói tin UDP tới {HOST}:{PORT} ở tần số {FPS} FPS")
    print("Chuỗi 5 pha: [1. Xòe tay] -> [2. Nắm đấm] -> [3. Đấm thẳng] -> [4. Đấm thủ] -> [5. Mất tay]")
    print("Mở scene 'Sandbox_Duy.unity' trong Unity Editor và nhấn PLAY để kiểm chứng.")
    print("Nhấn Ctrl+C để dừng.")
    print("=" * 80)

    t0 = time.time()
    frame_id = 0
    current_phase_name = ""
    last_strike_sent_time = 0.0
    hand_lost_sent_in_phase = False

    try:
        while True:
            now = time.time()
            elapsed = now - t0
            t_in_cycle = elapsed % CYCLE_DURATION
            t_ms = int(now * 1000)
            frame_id += 1

            # Xác định pha hiện tại
            phase_idx = int(t_in_cycle / 3.0)
            phase_idx = min(phase_idx, 4)
            phase_name, p_start, p_end = PHASES[phase_idx]
            progress_in_phase = (t_in_cycle - p_start) / (p_end - p_start)

            if phase_name != current_phase_name:
                current_phase_name = phase_name
                hand_lost_sent_in_phase = False
                print(f"\n>>> CHUYỂN PHA: {current_phase_name}")

            strike_event = None
            hand_lost_event = None
            include_left = True
            include_right = True

            if phase_idx == 0:
                # 1. XÒE BÀN TAY (OPEN_PALM): curl = 0
                curl_ratio = 0.0
                shape = "Open_Palm"
                hand_size = 0.14
                lx, ly, lz = 0.25, 0.50, 0.0
                rx, ry, rz = 0.75, 0.50, 0.0

                if progress_in_phase > 0.4 and (now - last_strike_sent_time) > 1.2:
                    strike_event = {
                        "type": "strike",
                        "t": t_ms,
                        "hand": "Left",
                        "kind": "OPEN_PALM",
                        "x": 0.25,
                        "y": 0.50
                    }
                    last_strike_sent_time = now

            elif phase_idx == 1:
                # 2. NẮM ĐẤM (CLOSED_FIST): curl co dần từ 0 lên 1.0
                curl_ratio = min(1.0, progress_in_phase * 2.0)
                shape = "Closed_Fist" if curl_ratio > 0.6 else "Open_Palm"
                hand_size = 0.12
                lx, ly, lz = 0.25, 0.50, 0.0
                rx, ry, rz = 0.75, 0.50, 0.0

            elif phase_idx == 2:
                # 3. ĐẤM THẲNG (PUNCH_STRAIGHT): Nắm đấm tay phải lao mạnh về phía trước
                curl_ratio = 1.0
                shape = "Closed_Fist"
                lunge_cycle = math.sin(progress_in_phase * math.pi * 3.0)
                lunge_intensity = max(0.0, lunge_cycle)

                hand_size = 0.12 + 0.08 * lunge_intensity
                lx, ly, lz = 0.25, 0.50, 0.0
                rx = 0.75 - 0.05 * lunge_intensity
                ry = 0.50 + 0.02 * lunge_intensity
                rz = -0.15 * lunge_intensity  # Lao về phía trước

                if lunge_intensity > 0.85 and (now - last_strike_sent_time) > 0.6:
                    strike_event = {
                        "type": "strike",
                        "t": t_ms,
                        "hand": "Right",
                        "kind": "PUNCH_STRAIGHT",
                        "x": round(rx, 4),
                        "y": round(ry, 4)
                    }
                    last_strike_sent_time = now

            elif phase_idx == 3:
                # 4. ĐẤM THỦ / PHÒNG THỦ (BLOCK): 2 tay đưa vào tư thế thủ
                curl_ratio = 1.0
                shape = "Closed_Fist"
                hand_size = 0.13
                lx, ly, lz = 0.35, 0.52, -0.05
                rx, ry, rz = 0.65, 0.52, -0.05

                if progress_in_phase > 0.3 and (now - last_strike_sent_time) > 1.0:
                    strike_event = {
                        "type": "strike",
                        "t": t_ms,
                        "hand": "Left",
                        "kind": "BLOCK",
                        "x": 0.35,
                        "y": 0.52
                    }
                    last_strike_sent_time = now

            else:
                # 5. THỬ NGHIỆM MẤT TAY (HAND_LOST): Tay Left rời khung hình
                curl_ratio = 0.5
                shape = "Open_Palm"
                hand_size = 0.12
                include_left = False  # Mất tay trái
                rx, ry, rz = 0.75, 0.50, 0.0

                if not hand_lost_sent_in_phase:
                    hand_lost_event = {
                        "type": "hand_lost",
                        "t": t_ms,
                        "hand": "Left"
                    }
                    hand_lost_sent_in_phase = True

            # Tạo mảng hands
            hands = []
            if include_left:
                left_lm = make_landmarks(lx, ly, lz, is_left=True, curl_ratio=curl_ratio)
                hands.append({
                    "hand": "Left",
                    "x": round(lx, 4),
                    "y": round(ly, 4),
                    "size": round(hand_size, 4),
                    "shape": shape,
                    "score": 0.98,
                    "lm": left_lm
                })

            if include_right:
                right_lm = make_landmarks(rx, ry, rz, is_left=False, curl_ratio=curl_ratio)
                hands.append({
                    "hand": "Right",
                    "x": round(rx, 4),
                    "y": round(ry, 4),
                    "size": round(hand_size, 4),
                    "shape": shape,
                    "score": 0.98,
                    "lm": right_lm
                })

            pose_msg = {
                "type": "pose",
                "t": t_ms,
                "frame": frame_id,
                "hands": hands
            }

            # Gửi gói Pose
            pose_bytes = json.dumps(pose_msg, separators=(",", ":")).encode("utf-8")
            sock.sendto(pose_bytes, (HOST, PORT))

            # Gửi gói Hand Lost nếu có
            if hand_lost_event:
                lost_bytes = json.dumps(hand_lost_event, separators=(",", ":")).encode("utf-8")
                sock.sendto(lost_bytes, (HOST, PORT))
                print(f"  [HAND_LOST GỬI ĐI] Tay {hand_lost_event['hand']} bị mất dấu")

            # Gửi gói Strike nếu có
            if strike_event:
                strike_bytes = json.dumps(strike_event, separators=(",", ":")).encode("utf-8")
                sock.sendto(strike_bytes, (HOST, PORT))
                print(f"  [STRIKE GỬI ĐI] {strike_event['kind']} bởi tay {strike_event['hand']} tại ({strike_event['x']}, {strike_event['y']})")

            time.sleep(1.0 / FPS)

    except KeyboardInterrupt:
        print("\n[SimulateHandStream] Đã dừng giả lập.")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
