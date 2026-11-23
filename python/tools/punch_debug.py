import cv2
import json
import os
import time
import math
import socket
from collections import deque
import numpy as np
import mediapipe as mp

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from punchar.capture import LatestFrameCapture
from punchar.decision import (
    OneEuroFilter,
    extract_hand_features,
    flatten_landmarks_21,
    get_corrected_handedness
)

# ==============================================================================
# CẤU HÌNH CAMERA & ĐƯỜNG DẪN DỮ LIỆU
# ==============================================================================
CAMERA_SRC = 1            # <--- ĐỔI ĐẦU VÀO CAMERA TẠI ĐÂY: 0, 1, 2... hoặc đường dẫn video
CAM_WIDTH = 1200          # (Gợi ý: đổi về 640x480 nếu cần tăng FPS khi chạy chung Unity)
CAM_HEIGHT = 960
DATA_DIR = ROOT_DIR / "data"
TEMPLATE_NPZ_FILE = str(DATA_DIR / "pose_templates.npz")
CONFIG_JSON_FILE = str(DATA_DIR / "pose_config.json")
ACTIVE_POSES = ["PUNCH_STRAIGHT", "OPEN_PALM", "BLOCK"]


# ==============================================================================
# HÀM ĐÓNG GÓI BẢN TIN UDP CHUẨN HỢP ĐỒNG + TRƯỜNG "lm" 3D MET (63 FLOAT)
# ==============================================================================
def flatten_landmarks_21(landmarks_src):
    """
    Chuyển 21 điểm landmarks (ưu tiên multi_hand_world_landmarks đơn vị mét)
    thành mảng phẳng 63 số thực làm tròn 4 chữ số để tính góc khớp 3D chính xác.
    """
    if landmarks_src is None:
        return None

    flat = []
    if hasattr(landmarks_src, "landmark"):
        pts = landmarks_src.landmark
        if len(pts) != 21:
            return None
        for p in pts:
            flat.append(round(float(p.x), 4))
            flat.append(round(float(1.0 - p.y), 4))
            flat.append(round(float(p.z), 4))
        return flat

    if len(landmarks_src) != 21:
        return None
    for p in landmarks_src:
        flat.append(round(float(p[0]), 4))
        flat.append(round(float(1.0 - p[1]), 4))
        flat.append(round(float(p[2]), 4))
    return flat


def build_pose_packet(timestamp_epoch_ms, pose_hands):
    """
    Đóng gói bản tin 'pose' gửi sang Unity (127.0.0.1:5005):
    - Giữ nguyên 4 trường hợp đồng nhóm: hand, x, y, shape
    - Đính kèm thêm mảng phẳng 'lm' (63 float 3D world_landmarks)
    """
    hands_payload = []
    for h in pose_hands:
        item = {
            "hand": h["hand"],
            "x": round(float(h["x"]), 4),
            "y": round(float(h["y"]), 4),
            "shape": h.get("shape", "None"),
        }
        lm_flat = flatten_landmarks_21(h.get("landmarks"))
        if lm_flat is not None and len(lm_flat) == 63:
            item["lm"] = lm_flat
        hands_payload.append(item)

    return {
        "type": "pose",
        "t": int(timestamp_epoch_ms),
        "hands": hands_payload,
    }


class DynamicGestureValidator:
    """
    Bộ kiểm duyệt cho từng tay:
    - PUNCH_STRAIGHT & OPEN_PALM: xét độc lập từng tay.
    - BLOCK: chỉ trả về cờ is_block_ready=True; quyền kích hoạt giao cho DualHandBlockCoordinator.
    """
    def __init__(self, hand_label, npz_data, config_data):
        self.hand_label = hand_label
        self.th = config_data["thresholds"]
        self.summary = config_data["templates_summary"].get(hand_label, {})
        self.vectors = {}

        for pose_name in ACTIVE_POSES:
            key_mean = f"{hand_label}_{pose_name}_mean_vec"
            if key_mean in npz_data and pose_name in self.summary:
                self.vectors[pose_name] = npz_data[key_mean]

        self.fx = OneEuroFilter()
        self.fy = OneEuroFilter()
        self.fs = OneEuroFilter()
        self.history = deque()

        self.state = "IDLE"
        self.cooldown_until_ms = 0
        self.last_valid_fist_ms = -9999
        self.last_valid_palm_ms = -9999

    def _compute_kinematics(self, x, y, s, t_ms):
        window_ms = self.th.get("window_ms", 120)
        self.history.append((t_ms, x, y, s))
        while len(self.history) > 1 and (t_ms - self.history[0][0]) > window_ms:
            self.history.popleft()

        v_scale, scale_gain, v_planar = 0.0, 0.0, 0.0
        if len(self.history) >= 2:
            t0, x0, y0, s0 = self.history[0]
            dt_sec = (t_ms - t0) / 1000.0
            if dt_sec >= 0.025:
                scale_gain = (s - s0) / max(s0, 1e-4)
                v_scale = scale_gain / dt_sec
                v_planar = math.hypot(x - x0, y - y0) / (max(s, 0.05) * dt_sec)
        return v_scale, scale_gain, v_planar

    def _compute_pose_and_motion_conf(self, feat, v_scale, scale_gain, v_planar, mp_conf):
        pose_confs = {p: 0.0 for p in ACTIVE_POSES}
        motion_confs = {p: 0.0 for p in ACTIVE_POSES}
        total_confs = {p: 0.0 for p in ACTIVE_POSES}

        sigma_shape = self.th.get("shape_sigma", 0.20)

        for pose_name, tpl_vec in self.vectors.items():
            tpl_stat = self.summary[pose_name]

            shape_err = float(np.linalg.norm(feat["shape_vec"] - tpl_vec) / np.sqrt(len(tpl_vec)))
            c_shape = math.exp(-(shape_err ** 2) / (2.0 * (sigma_shape ** 2)))

            mean_ro = tpl_stat["mean_r_open"]
            std_ro = max(tpl_stat.get("std_r_open", 0.12), 0.12)
            c_open = math.exp(-((feat["r_open"] - mean_ro) ** 2) / (2.0 * ((std_ro + 0.15) ** 2)))

            p_conf = mp_conf * (0.65 * c_shape + 0.35 * c_open) * 100.0
            pose_confs[pose_name] = round(float(np.clip(p_conf, 0.0, 100.0)), 1)

            if pose_name == "PUNCH_STRAIGHT":
                req_v = self.th.get("punch_min_vel_scale", 1.30)
                req_g = self.th.get("punch_min_scale_gain", 0.15)
                c_vel = min(1.0, max(0.0, v_scale) / req_v)
                c_gain = min(1.0, max(0.0, scale_gain) / req_g)
                m_conf = (0.60 * c_vel + 0.40 * c_gain) * 100.0
            elif pose_name == "OPEN_PALM":
                req_v = self.th.get("palm_min_vel_scale", 0.90)
                req_g = self.th.get("palm_min_scale_gain", 0.12)
                c_vel = min(1.0, max(0.0, v_scale) / req_v)
                c_gain = min(1.0, max(0.0, scale_gain) / req_g)
                m_conf = (0.60 * c_vel + 0.40 * c_gain) * 100.0
            else:
                max_vp = self.th.get("block_max_planar_vel", 0.85)
                c_still = max(0.0, 1.0 - (v_planar / (max_vp * 1.6)))
                m_conf = c_still * 100.0

            motion_confs[pose_name] = round(float(np.clip(m_conf, 0.0, 100.0)), 1)
            total_confs[pose_name] = round(0.50 * pose_confs[pose_name] + 0.50 * motion_confs[pose_name], 1)

        return pose_confs, motion_confs, total_confs

    def process(self, feat, mp_conf, t_ms, world_landmarks=None, raw_landmarks=None):
        x = self.fx.filter(feat["x"], t_ms)
        y = self.fy.filter(feat["y"], t_ms)
        s = self.fs.filter(feat["hand_size"], t_ms)
        r_open = feat["r_open"]

        v_scale, scale_gain, v_planar = self._compute_kinematics(x, y, s, t_ms)
        pose_confs, motion_confs, total_confs = self._compute_pose_and_motion_conf(
            feat, v_scale, scale_gain, v_planar, mp_conf
        )

        min_p_conf = self.th.get("min_pose_confidence_pct", 68.0)
        if mp_conf >= self.th["min_mp_confidence"]:
            if pose_confs.get("PUNCH_STRAIGHT", 0.0) >= min_p_conf and r_open <= self.th["fist_max_r_open"]:
                self.last_valid_fist_ms = t_ms
            if pose_confs.get("OPEN_PALM", 0.0) >= min_p_conf and r_open >= self.th["palm_min_r_open"]:
                self.last_valid_palm_ms = t_ms

        static_shape = "Open_Palm" if r_open >= self.th["palm_min_r_open"] else (
            "Closed_Fist" if r_open <= self.th["fist_max_r_open"] else "None"
        )

        lm_source = world_landmarks if world_landmarks is not None else (
            raw_landmarks if raw_landmarks is not None else feat.get("landmarks")
        )
        pose_item = {
            "hand": self.hand_label,
            "x": round(x, 4),
            "y": round(1.0 - y, 4),
            "shape": static_shape,
            "landmarks": lm_source,
        }

        best_pose = max(pose_confs, key=pose_confs.get) if len(pose_confs) > 0 else "NONE"
        kin_info = {"v_scale": v_scale, "scale_gain": scale_gain, "v_planar": v_planar}

        def make_result(strike_ev, is_valid, pose_name, reason, is_block_ready=False):
            return {
                "hand": self.hand_label,
                "pose_item": pose_item,
                "strike_ev": strike_ev,
                "is_valid": is_valid,
                "best_pose": pose_name,
                "pose_confs": pose_confs,
                "motion_confs": motion_confs,
                "total_confs": total_confs,
                "kin_info": kin_info,
                "reason": reason,
                "mp_conf": mp_conf,
                "is_block_ready": is_block_ready,
            }

        # Cổng 1: Phân làn Trái / Phải
        if self.hand_label == "Left" and x > 0.58:
            self.state = "IDLE"
            return make_result(None, False, best_pose, "Sai lan (Sang Phai)")
        if self.hand_label == "Right" and x < 0.42:
            self.state = "IDLE"
            return make_result(None, False, best_pose, "Sai lan (Sang Trai)")

        # Cổng 2: Cooldown sau cú Đấm / Xoè đẩy
        if t_ms < self.cooldown_until_ms:
            rem = self.cooldown_until_ms - t_ms
            self.state = "COOLDOWN"
            return make_result(None, True, best_pose, f"COOLDOWN ({rem}ms)")

        grace_ms = self.th.get("blur_grace_ms", 60)
        fist_ready = (pose_confs.get("PUNCH_STRAIGHT", 0.0) >= min_p_conf) or ((t_ms - self.last_valid_fist_ms) <= grace_ms)
        palm_ready = (pose_confs.get("OPEN_PALM", 0.0) >= min_p_conf) or ((t_ms - self.last_valid_palm_ms) <= grace_ms)

        # Cổng 3: ĐẤM THẲNG (PUNCH_STRAIGHT) — xét độc lập từng tay
        if fist_ready and r_open <= self.th["fist_max_r_open"] + 0.08:
            req_v = self.th.get("punch_min_vel_scale", 1.30)
            req_g = self.th.get("punch_min_scale_gain", 0.15)
            if v_scale >= req_v and scale_gain >= req_g:
                self.state = "STRIKE"
                self.cooldown_until_ms = t_ms + self.th["cooldown_ms"]
                strike_ev = {
                    "type": "strike", "t": t_ms, "hand": self.hand_label,
                    "kind": "PUNCH_STRAIGHT", "x": round(x, 4), "y": round(1.0 - y, 4)
                }
                return make_result(strike_ev, True, "PUNCH_STRAIGHT", "VALID STRIKE: PUNCH!")
            elif v_scale >= 0.55 * req_v:
                self.state = "WINDUP"
                return make_result(None, False, "PUNCH_STRAIGHT", f"WINDUP DAM (v={v_scale:.2f}/s)")

        # Cổng 4: XOÈ ĐẨY (OPEN_PALM) — xét độc lập từng tay
        if palm_ready and r_open >= self.th["palm_min_r_open"] - 0.05:
            req_v = self.th.get("palm_min_vel_scale", 0.90)
            req_g = self.th.get("palm_min_scale_gain", 0.12)
            if v_scale >= req_v and scale_gain >= req_g:
                self.state = "STRIKE"
                self.cooldown_until_ms = t_ms + self.th["cooldown_ms"]
                strike_ev = {
                    "type": "strike", "t": t_ms, "hand": self.hand_label,
                    "kind": "OPEN_PALM", "x": round(x, 4), "y": round(1.0 - y, 4)
                }
                return make_result(strike_ev, True, "OPEN_PALM", "VALID STRIKE: OPEN_PALM!")
            else:
                self.state = "STANDBY_PALM"
                return make_result(None, False, "OPEN_PALM", "DUNG POSE (Hay DAY TAY ve truoc!)")

        # Cổng 5: Kiểm tra điều kiện THỦ (BLOCK) của riêng tay này (chưa kích hoạt, chờ ghép 2 tay)
        if (
            mp_conf >= self.th["min_mp_confidence"]
            and pose_confs.get("BLOCK", 0.0) >= min_p_conf
            and r_open <= self.th["fist_max_r_open"]
        ):
            is_still = (
                v_planar <= self.th.get("block_max_planar_vel", 0.85)
                and abs(v_scale) <= self.th.get("block_max_scale_vel", 0.65)
            )
            in_zone = (0.18 <= y <= 0.82)
            if is_still and in_zone:
                self.state = "BLOCK_READY"
                return make_result(
                    None, False, "BLOCK",
                    "Cho tay kia cung thu (BLOCK 2 tay)",
                    is_block_ready=True
                )

        self.state = "IDLE"
        return make_result(None, False, best_pose, "Chua du dieu kien")


class DualHandBlockCoordinator:
    """
    Điều phối cử chỉ THỦ (BLOCK) bắt buộc ĐỒNG THỜI CẢ 2 TAY (Left + Right):
    - Chỉ khi cả 2 tay cùng có mặt và đạt điều kiện BLOCK tĩnh trong vùng thủ mới bắt đầu đếm hold_ms.
    - Đạt đủ block_hold_ms -> phát đồng bộ gói strike BLOCK cho cả 2 tay và khóa DEFENDING chống lặp.
    - Chỉ cần 1 trong 2 tay hạ xuống/rời khung hình/di chuyển -> reset ngay lập tức.
    """
    def __init__(self, thresholds):
        self.th = thresholds
        self.hold_start_ms = None
        self.is_defending_locked = False

    def update(self, frame_outputs, validators, t_now_ms, t_epoch_ms):
        left_out = frame_outputs.get("Left")
        right_out = frame_outputs.get("Right")

        both_ready = (
            left_out is not None
            and right_out is not None
            and left_out["is_block_ready"]
            and right_out["is_block_ready"]
        )

        if both_ready:
            if self.hold_start_ms is None:
                self.hold_start_ms = t_now_ms

            held_ms = t_now_ms - self.hold_start_ms
            req_hold = self.th.get("block_hold_ms", 120)

            if held_ms >= req_hold:
                if not self.is_defending_locked:
                    self.is_defending_locked = True
                    for side, out in (("Left", left_out), ("Right", right_out)):
                        validators[side].state = "DEFENDING"
                        out["is_valid"] = True
                        out["best_pose"] = "BLOCK"
                        out["reason"] = "VALID STRIKE: BLOCK (2 TAY)!"
                        out["strike_ev"] = {
                            "type": "strike",
                            "t": t_epoch_ms,
                            "hand": side,
                            "kind": "BLOCK",
                            "x": out["pose_item"]["x"],
                            "y": out["pose_item"]["y"],
                        }
                else:
                    for side, out in (("Left", left_out), ("Right", right_out)):
                        validators[side].state = "DEFENDING"
                        out["is_valid"] = True
                        out["best_pose"] = "BLOCK"
                        out["reason"] = "HOP LE (DANG GIU THU 2 TAY)"
            else:
                for side, out in (("Left", left_out), ("Right", right_out)):
                    validators[side].state = "HOLDING_BLOCK"
                    out["is_valid"] = False
                    out["best_pose"] = "BLOCK"
                    out["reason"] = f"Dang giu BLOCK 2 tay: {held_ms}/{req_hold}ms"
        else:
            self.hold_start_ms = None
            self.is_defending_locked = False

            # Nếu chỉ có 1 tay đang vào thế thủ -> báo rõ chưa hợp lệ vì thiếu tay còn lại
            for side, out in frame_outputs.items():
                if out["is_block_ready"]:
                    other_vn = "Phai" if side == "Left" else "Trai"
                    out["is_valid"] = False
                    out["best_pose"] = "BLOCK"
                    out["reason"] = f"Thieu tay {other_vn} (Can 2 tay BLOCK)"


def draw_interactive_hud(frame, hand_label, pose_confs, motion_confs, total_confs, kin_info, mp_conf, best_pose, is_valid):
    h, w, _ = frame.shape
    panel_x = 10 if hand_label == "Left" else w - 305
    panel_y = h - 125

    overlay = frame.copy()
    cv2.rectangle(overlay, (panel_x - 5, panel_y - 24), (panel_x + 295, h - 6), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

    hdr_col = (0, 255, 0) if is_valid else (0, 215, 255)
    cv2.putText(frame, f"{hand_label.upper()} | MP:{mp_conf*100:.0f}% | v_scale:{kin_info['v_scale']:+.2f}/s (gain:{kin_info['scale_gain']*100:+.0f}%)",
                (panel_x, panel_y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.41, hdr_col, 1)

    for idx, p_name in enumerate(ACTIVE_POSES):
        p_c = pose_confs.get(p_name, 0.0)
        m_c = motion_confs.get(p_name, 0.0)
        t_c = total_confs.get(p_name, 0.0)
        y_row = panel_y + 22 * (idx + 1)
        short = p_name.replace("PUNCH_STRAIGHT", "PUNCH")

        cv2.putText(frame, f"{short:<9} Pose:{p_c:>4.0f}% | Mot:{m_c:>4.0f}%",
                    (panel_x, y_row), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (235, 235, 235), 1)

        bar_x = panel_x + 205
        cv2.rectangle(frame, (bar_x, y_row - 10), (bar_x + 82, y_row - 1), (65, 65, 65), -1)
        bar_w = int(82 * (t_c / 100.0))
        bar_col = (0, 255, 0) if (p_name == best_pose and is_valid) else (0, 165, 255)
        cv2.rectangle(frame, (bar_x, y_row - 10), (bar_x + bar_w, y_row - 1), bar_col, -1)


def main():
    if not os.path.exists(TEMPLATE_NPZ_FILE) or not os.path.exists(CONFIG_JSON_FILE):
        print(f"[!] Chua tim thay '{TEMPLATE_NPZ_FILE}' hoac '{CONFIG_JSON_FILE}'.")
        print("    Hay chay 'python 1_collect_and_label.py' va nhan 's' de luu du lieu truoc!")
        return

    npz_data = np.load(TEMPLATE_NPZ_FILE)
    with open(CONFIG_JSON_FILE, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    th = config_data["thresholds"]
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_target = (th["udp_host"], int(th["udp_port"]))

    mp_hands = mp.solutions.hands
    mp_draw = mp.solutions.drawing_utils
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.60,
        min_tracking_confidence=0.60
    )

    validators = {
        "Left": DynamicGestureValidator("Left", npz_data, config_data),
        "Right": DynamicGestureValidator("Right", npz_data, config_data)
    }
    dual_block = DualHandBlockCoordinator(th)
    prev_hands = set()

    try:
        cam = LatestFrameCapture(src=CAMERA_SRC, width=CAM_WIDTH, height=CAM_HEIGHT, fps=30)
    except RuntimeError as e:
        print(f"[!] LOI KHOI TAO CAMERA: {e}")
        hands.close()
        udp_sock.close()
        return

    prev_clock = time.perf_counter()
    fps = 30.0
    print(f"[PunchAR] Dang phat UDP (pose + 3D world_lm[63] + strike | BLOCK = 2 TAY) toi {udp_target[0]}:{udp_target[1]}...")

    try:
        while True:
            ret, frame, t_capture_ms = cam.read()
            if not ret:
                time.sleep(0.005)
                continue

            now = time.perf_counter()
            fps = 0.9 * fps + 0.1 * (1.0 / max(now - prev_clock, 1e-4))
            prev_clock = now

            h, w, _ = frame.shape
            cv2.line(frame, (w // 2, 0), (w // 2, h), (180, 180, 180), 1)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            t_now_ms = int(time.perf_counter() * 1000)
            latency_ms = max(0, t_now_ms - t_capture_ms)
            t_epoch_ms = int(time.time() * 1000) - latency_ms

            # ------------------------------------------------------------------
            # LƯỢT 1: Lọc trùng nhãn (nếu có) và xử lý từng tay độc lập
            # ------------------------------------------------------------------
            detected_by_side = {}
            if results.multi_hand_landmarks and results.multi_handedness:
                world_list = results.multi_hand_world_landmarks or [None] * len(results.multi_hand_landmarks)
                for lm, wlm, handedness in zip(results.multi_hand_landmarks, world_list, results.multi_handedness):
                    hand_label, mp_conf = get_corrected_handedness(handedness, invert_handedness=False)
                    if hand_label not in detected_by_side or mp_conf > detected_by_side[hand_label][2]:
                        detected_by_side[hand_label] = (lm, wlm, mp_conf)

            frame_outputs = {}
            for hand_label, (lm, wlm, mp_conf) in detected_by_side.items():
                feat = extract_hand_features(lm)
                out = validators[hand_label].process(
                    feat, mp_conf, t_now_ms, world_landmarks=wlm, raw_landmarks=lm
                )
                out["raw_lm"] = lm
                frame_outputs[hand_label] = out

            # ------------------------------------------------------------------
            # LƯỢT 2: Xét điều kiện THỦ (BLOCK) đồng thời cả 2 tay
            # ------------------------------------------------------------------
            dual_block.update(frame_outputs, validators, t_now_ms, t_epoch_ms)

            # ------------------------------------------------------------------
            # LƯỢT 3: Gửi UDP strike + Vẽ khung xương & HUD với kết quả cuối cùng
            # ------------------------------------------------------------------
            current_hands = set(frame_outputs.keys())
            pose_hands = []

            for hand_label, out in frame_outputs.items():
                pose_item = out["pose_item"]
                strike_ev = out["strike_ev"]
                is_valid = out["is_valid"]
                best_pose = out["best_pose"]
                pose_confs = out["pose_confs"]
                motion_confs = out["motion_confs"]
                total_confs = out["total_confs"]
                kin_info = out["kin_info"]
                reason = out["reason"]
                mp_conf = out["mp_conf"]
                lm = out["raw_lm"]

                pose_hands.append(pose_item)

                if strike_ev is not None:
                    strike_ev["t"] = t_epoch_ms
                    udp_sock.sendto(json.dumps(strike_ev).encode("utf-8"), udp_target)
                    print(f"[STRIKE HOP LE] {hand_label} -> {strike_ev['kind']} | "
                          f"Pose:{pose_confs[best_pose]:.0f}% Mot:{motion_confs[best_pose]:.0f}% | "
                          f"v_scale:{kin_info['v_scale']:+.2f}/s | Latency:{latency_ms}ms")

                mp_draw.draw_landmarks(frame, lm, mp_hands.HAND_CONNECTIONS)
                cx, cy = int(pose_item["x"] * w), int(pose_item["y"] * h)
                color = (0, 255, 0) if is_valid else (
                    (0, 215, 255) if pose_confs.get(best_pose, 0.0) >= 68.0 else (0, 0, 255)
                )

                cv2.circle(frame, (cx, cy), 8, color, -1)
                line1 = f"[{hand_label}] {best_pose} | Pose:{pose_confs.get(best_pose,0):.0f}% Mot:{motion_confs.get(best_pose,0):.0f}%"
                line2 = f"{reason}"
                cv2.putText(frame, line1, (max(10, cx - 125), max(45, cy - 30)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.50, color, 2)
                cv2.putText(frame, line2, (max(10, cx - 125), max(65, cy - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.48, color, 2)

                draw_interactive_hud(frame, hand_label, pose_confs, motion_confs,
                                     total_confs, kin_info, mp_conf, best_pose, is_valid)

            pose_packet = build_pose_packet(t_epoch_ms, pose_hands)
            udp_sock.sendto(json.dumps(pose_packet).encode("utf-8"), udp_target)

            for lost_hand in (prev_hands - current_hands):
                lost_packet = {"type": "hand_lost", "t": t_epoch_ms, "hand": lost_hand}
                udp_sock.sendto(json.dumps(lost_packet).encode("utf-8"), udp_target)
            prev_hands = current_hands

            block_badge = " | [BLOCK 2 TAY: ACTIVE]" if dual_block.is_defending_locked else ""
            cv2.rectangle(frame, (0, 0), (w, 28), (20, 20, 20), -1)
            cv2.putText(
                frame,
                f"DYNAMIC GESTURE HUD | FPS: {fps:.1f} | Latency: {latency_ms} ms | UDP(3D-LM) -> {udp_target[0]}:{udp_target[1]}{block_badge}",
                (12, 19),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                (0, 255, 0) if dual_block.is_defending_locked else (0, 255, 255),
                1
            )

            cv2.imshow("2. Dynamic Gesture & Kinematics Validator", frame)
            if (cv2.waitKey(1) & 0xFF) == ord('q'):
                break

    finally:
        cam.release()
        hands.close()
        udp_sock.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()