import os
import cv2
import json
import time
import math
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
    get_corrected_handedness
)

# ==============================================================================
# CẤU HÌNH CAMERA & ĐƯỜNG DẪN LƯU TRỮ (.NPZ + .JSON + HÌNH ẢNH)
# ==============================================================================
CAMERA_SRC = 1            # <--- ĐỔI ĐẦU VÀO CAMERA TẠI ĐÂY: 0, 1, 2... hoặc đường dẫn video
camHeight = 960
camWight = 1200 
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATASET_NPZ_FILE = str(DATA_DIR / "gesture_dataset.npz")
TEMPLATE_NPZ_FILE = str(DATA_DIR / "pose_templates.npz")
CONFIG_JSON_FILE = str(DATA_DIR / "pose_config.json")
DATASET_IMAGE_DIR = str(DATA_DIR / "dataset_images")
TARGET_SAMPLES_PER_POSE = 50  #<== thu nhận số mẫu

POSE_LIST = ["PUNCH_STRAIGHT", "OPEN_PALM", "BLOCK", "IDLE"]

POSE_RULES = {
    "PUNCH_STRAIGHT": {
        "min_mp_conf": 0.70,
        "max_r_open": 1.28,
        "min_hand_size": 0.10,
        "guide_text": "Nam chat tay + Dam/Vuon ve camera (Nhan SPACE de dem nguoc 3s)"
    },
    "OPEN_PALM": {
        "min_mp_conf": 0.70,
        "min_r_open": 1.50,
        "min_hand_size": 0.09,
        "guide_text": "Xoe cang 5 ngon + Day long ban tay ve truoc (Nhan SPACE de dem nguoc 3s)"
    },
    "BLOCK": {
        "min_mp_conf": 0.70,
        "max_r_open": 1.28,
        "zone_y": [0.18, 0.82],
        "guide_text": "Nam kin tay + Giu yen vung Thu truoc mat (Nhan SPACE de dem nguoc 3s)"
    },
    "IDLE": {
        "min_mp_conf": 0.55,
        "guide_text": "Tha long / Dua tay tu nhien (Nhan SPACE de dem nguoc 3s)"
    }
}


class KinematicTracker:
    """Tính vận tốc phóng to (v_scale), biên độ đẩy (scale_gain) và vận tốc phẳng (v_planar) trên cửa sổ 120ms."""
    def __init__(self, window_ms=120):
        self.window_ms = window_ms
        self.fx = OneEuroFilter()
        self.fy = OneEuroFilter()
        self.fs = OneEuroFilter()
        self.history = deque()

    def update(self, raw_x, raw_y, raw_size, t_ms):
        x = self.fx.filter(raw_x, t_ms)
        y = self.fy.filter(raw_y, t_ms)
        s = self.fs.filter(raw_size, t_ms)

        self.history.append((t_ms, x, y, s))
        while len(self.history) > 1 and (t_ms - self.history[0][0]) > self.window_ms:
            self.history.popleft()

        v_scale = 0.0
        scale_gain = 0.0
        v_planar = 0.0

        if len(self.history) >= 2:
            t0, x0, y0, s0 = self.history[0]
            dt_sec = (t_ms - t0) / 1000.0
            if dt_sec >= 0.025:
                scale_gain = (s - s0) / max(s0, 1e-4)
                v_scale = scale_gain / dt_sec
                dist_2d = math.hypot(x - x0, y - y0)
                v_planar = dist_2d / (max(s, 0.05) * dt_sec)

        return x, y, s, v_scale, scale_gain, v_planar


def validate_sample_for_pose(feat, hand_label, mp_conf, pose_name):
    rule = POSE_RULES[pose_name]
    if mp_conf < rule["min_mp_conf"]:
        return False, f"MP Conf thap ({mp_conf*100:.0f}%)"
    if not feat["in_bounds"]:
        return False, "Ban tay tran bien khung hinh"
    if hand_label == "Left" and feat["x"] > 0.58:
        return False, "Sai lan: Tay Trai o ben Phai"
    if hand_label == "Right" and feat["x"] < 0.42:
        return False, "Sai lan: Tay Phai o ben Trai"

    r_open = feat["r_open"]
    h_size = feat["hand_size"]

    if pose_name == "PUNCH_STRAIGHT":
        if r_open > rule["max_r_open"]:
            return False, f"Tay chua nam chat (r_open={r_open:.2f})"
        if h_size < rule["min_hand_size"]:
            return False, f"Tay qua xa cam (size={h_size:.2f})"
    elif pose_name == "OPEN_PALM":
        if r_open < rule["min_r_open"]:
            return False, f"Chua xoe cang 5 ngon (r_open={r_open:.2f})"
        if h_size < rule["min_hand_size"]:
            return False, f"Tay qua xa cam (size={h_size:.2f})"
    elif pose_name == "BLOCK":
        if r_open > rule["max_r_open"]:
            return False, f"The thu phai nam kin (r_open={r_open:.2f})"
        zy = rule["zone_y"]
        if not (zy[0] <= feat["y"] <= zy[1]):
            return False, f"Ngoai vung Thu (y={feat['y']:.2f})"

    return True, "MAU HOP LE (VALID)"


def save_all_data(collected, save_images=True):
    all_ts, all_hands, all_labels = [], [], []
    all_vecs, all_landmarks, all_metrics = [], [], []
    template_npz_dict = {}

    config_json = {
        "metadata": {
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "storage_format": "NPZ + JSON Hybrid (Pose + Kinematics + Images)"
        },
        "thresholds": {
            "min_mp_confidence": 0.70,
            "min_pose_confidence_pct": 68.0,
            "min_total_confidence_pct": 70.0,
            "shape_sigma": 0.20,
            "window_ms": 120,
            "blur_grace_ms": 60,
            "cooldown_ms": 250,
            "block_hold_ms": 120,
            "punch_min_vel_scale": 1.30,
            "punch_min_scale_gain": 0.15,
            "palm_min_vel_scale": 0.90,
            "palm_min_scale_gain": 0.12,
            "block_max_planar_vel": 0.85,
            "block_max_scale_vel": 0.65,
            "palm_min_r_open": 1.48,
            "fist_max_r_open": 1.28,
            "udp_host": "127.0.0.1",
            "udp_port": 5005
        },
        "templates_summary": {"Left": {}, "Right": {}}
    }

    total_samples = 0
    saved_images_count = 0

    for side in ["Left", "Right"]:
        for pose_name in POSE_LIST:
            samples = collected[side][pose_name]
            if len(samples) == 0:
                continue

            # Tao thu muc luu anh rieng cho tung tay va the
            if save_images:
                pose_dir = os.path.join(DATASET_IMAGE_DIR, side, pose_name)
                os.makedirs(pose_dir, exist_ok=True)

            for idx, s in enumerate(samples):
                all_ts.append(s["ts"])
                all_hands.append(side)
                all_labels.append(pose_name)
                all_vecs.append(s["shape_vec"])
                all_landmarks.append(s["landmarks"])
                all_metrics.append([
                    s["x"], s["y"], s["hand_size"], s["r_open"],
                    s["v_scale"], s["scale_gain"], s["v_planar"], s["mp_conf"]
                ])
                total_samples += 1

                # Luu hinh anh clean frame va anh crop ban tay
                if save_images and "clean_frame" in s and s["clean_frame"] is not None:
                    cf = s["clean_frame"]
                    h, w, _ = cf.shape
                    base_name = f"sample_{idx:03d}_{s['ts']}"

                    # 1. Luu toan bo khung hinh sach (khong co HUD)
                    cv2.imwrite(os.path.join(pose_dir, f"{base_name}_full.jpg"), cf)

                    # 2. Luu vung cat ban tay (Hand ROI crop)
                    lms = s["landmarks"]
                    xmin = max(0, int(np.min(lms[:, 0]) * w) - 24)
                    ymin = max(0, int(np.min(lms[:, 1]) * h) - 24)
                    xmax = min(w, int(np.max(lms[:, 0]) * w) + 24)
                    ymax = min(h, int(np.max(lms[:, 1]) * h) + 24)
                    if xmax > xmin and ymax > ymin:
                        crop = cf[ymin:ymax, xmin:xmax]
                        cv2.imwrite(os.path.join(pose_dir, f"{base_name}_crop.jpg"), crop)

                    saved_images_count += 1

            if pose_name != "IDLE":
                vecs = np.array([s["shape_vec"] for s in samples], dtype=np.float32)
                sizes = np.array([s["hand_size"] for s in samples], dtype=np.float32)
                r_opens = np.array([s["r_open"] for s in samples], dtype=np.float32)
                xs = np.array([s["x"] for s in samples], dtype=np.float32)
                ys = np.array([s["y"] for s in samples], dtype=np.float32)

                key_prefix = f"{side}_{pose_name}"
                template_npz_dict[f"{key_prefix}_mean_vec"] = np.mean(vecs, axis=0)
                template_npz_dict[f"{key_prefix}_std_vec"] = np.std(vecs, axis=0) + 1e-4

                config_json["templates_summary"][side][pose_name] = {
                    "num_samples": len(samples),
                    "mean_hand_size": round(float(np.mean(sizes)), 4),
                    "std_hand_size": round(float(np.std(sizes) + 1e-4), 4),
                    "mean_r_open": round(float(np.mean(r_opens)), 4),
                    "std_r_open": round(float(np.std(r_opens) + 1e-4), 4),
                    "pos_box": [
                        round(float(np.percentile(xs, 5)), 4),
                        round(float(np.percentile(ys, 5)), 4),
                        round(float(np.percentile(xs, 95)), 4),
                        round(float(np.percentile(ys, 95)), 4)
                    ]
                }

    if total_samples == 0:
        return False, "Chua co mau nao! Hay giu SPACE hoac phim 1,2,3 de thu mau."

    np.savez_compressed(
        DATASET_NPZ_FILE,
        timestamps=np.array(all_ts, dtype=np.int64),
        hands=np.array(all_hands),
        labels=np.array(all_labels),
        shape_vecs=np.array(all_vecs, dtype=np.float32),
        landmarks=np.array(all_landmarks, dtype=np.float32),
        metrics=np.array(all_metrics, dtype=np.float32)
    )
    np.savez_compressed(TEMPLATE_NPZ_FILE, **template_npz_dict)
    with open(CONFIG_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(config_json, f, indent=2, ensure_ascii=False)

    msg = (f"Da luu {total_samples} mau vao '{TEMPLATE_NPZ_FILE}', '{CONFIG_JSON_FILE}' "
           f"va {saved_images_count} anh vao '{DATASET_IMAGE_DIR}/'!")
    return True, msg


def draw_collection_hud(frame, selected_pose, is_recording, collected, status_banner, banner_color, fps, countdown_sec=None):
    h, w, _ = frame.shape
    cv2.line(frame, (w // 2, 0), (w // 2, h), (180, 180, 180), 1)
    cv2.rectangle(frame, (int(0.10 * w), int(0.18 * h)),
                  (int(0.90 * w), int(0.82 * h)), (120, 120, 255), 1)

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 88), (20, 20, 20), -1)
    cv2.rectangle(overlay, (0, h - 95), (w, h), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

    if countdown_sec is not None:
        rec_badge = f"[DEM NGUOC: {int(math.ceil(countdown_sec))}s]"
        rec_color = (0, 215, 255)
    elif is_recording:
        rec_badge = f"[DANG THU MAU - REC (DEN KHI DU {TARGET_SAMPLES_PER_POSE} MAU)]"
        rec_color = (0, 0, 255)
    else:
        rec_badge = "[CHE DO CHO - STANDBY]"
        rec_color = (0, 215, 255)

    cv2.putText(frame, f"POSE: {selected_pose}  {rec_badge}  | FPS: {fps:.1f}",
                (12, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.52, rec_color, 2)
    cv2.putText(frame, f"Huong dan: {POSE_RULES[selected_pose]['guide_text']}",
                (12, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (230, 230, 230), 1)
    cv2.putText(frame, status_banner, (12, 76), cv2.FONT_HERSHEY_SIMPLEX, 0.50, banner_color, 2)

    # Hop dem nguoc 3s o giua man hinh
    if countdown_sec is not None and countdown_sec > 0:
        box_w, box_h = 320, 150
        bx1, by1 = (w - box_w) // 2, (h - box_h) // 2
        bx2, by2 = bx1 + box_w, by1 + box_h

        sub_overlay = frame.copy()
        cv2.rectangle(sub_overlay, (bx1, by1), (bx2, by2), (20, 20, 20), -1)
        cv2.addWeighted(sub_overlay, 0.82, frame, 0.18, 0, frame)
        cv2.rectangle(frame, (bx1, by1), (bx2, by2), (0, 215, 255), 2)

        cv2.putText(frame, "CHUAN BI THU MAU", (bx1 + 38, by1 + 38),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (230, 230, 230), 2)
        count_str = str(int(math.ceil(countdown_sec)))
        cv2.putText(frame, count_str, (bx1 + 130, by1 + 118),
                    cv2.FONT_HERSHEY_SIMPLEX, 2.3, (0, 215, 255), 4)

    elif is_recording:
        # Cham do REC o goc tren ben phai
        cv2.circle(frame, (w - 25, 25), 8, (0, 0, 255), -1)
        cv2.putText(frame, "REC", (w - 65, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2)

    y_base = h - 70
    for side in ["Left", "Right"]:
        x_offset = 12 if side == "Left" else w // 2 + 10
        cv2.putText(frame, f"=== TAY {side.upper()} ===", (x_offset, y_base),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 255), 1)
        for idx, p_name in enumerate(["PUNCH_STRAIGHT", "OPEN_PALM", "BLOCK"]):
            cnt = len(collected[side][p_name])
            ratio = min(1.0, cnt / TARGET_SAMPLES_PER_POSE)
            py = y_base + 18 * (idx + 1)
            cv2.putText(frame, f"{p_name[:10]:<10}: {cnt:>2}/{TARGET_SAMPLES_PER_POSE}",
                        (x_offset, py), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (255, 255, 255), 1)
            bar_x = x_offset + 145
            cv2.rectangle(frame, (bar_x, py - 10), (bar_x + 110, py - 1), (70, 70, 70), -1)
            bar_color = (0, 255, 0) if ratio >= 1.0 else (0, 180, 255)
            cv2.rectangle(frame, (bar_x, py - 10), (bar_x + int(110 * ratio), py - 1), bar_color, -1)


def main():
    mp_hands = mp.solutions.hands
    mp_draw = mp.solutions.drawing_utils
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.60,
        min_tracking_confidence=0.60
    )

    collected = {"Left": {p: [] for p in POSE_LIST}, "Right": {p: [] for p in POSE_LIST}}
    trackers = {"Left": KinematicTracker(120), "Right": KinematicTracker(120)}

    selected_pose = "PUNCH_STRAIGHT"
    status_banner = "1/2/3/0: Chon Pose | SPACE: Dem nguoc 3s & Thu mau | C: Chup | S: Luu | Q: Thoat"
    banner_color = (200, 200, 200)

    COUNTDOWN_DURATION = 3.0    # 3 giay dem nguoc
    app_state = "STANDBY"       # "STANDBY" | "COUNTDOWN" | "RECORDING"
    countdown_start_t = 0.0

    try:
        cam = LatestFrameCapture(src=CAMERA_SRC, width= camWight, height= camHeight, fps=30)
    except RuntimeError as e:
        print(f"[!] LOI KHOI TAO CAMERA: {e}")
        return

    prev_time = time.perf_counter()
    fps = 30.0

    key_map = {
        ord('1'): "PUNCH_STRAIGHT",
        ord('2'): "OPEN_PALM",
        ord('3'): "BLOCK",
        ord('0'): "IDLE"
    }

    try:
        while True:
            ret, frame, ts_ms = cam.read()
            if not ret:
                time.sleep(0.005)
                continue

            now = time.perf_counter()
            fps = 0.9 * fps + 0.1 * (1.0 / max(now - prev_time, 1e-4))
            prev_time = now

            # Luu ban copy sach khong co overlay HUD de ghi anh dataset
            clean_frame = frame.copy()

            h, w, _ = frame.shape
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            key = cv2.waitKey(1) & 0xFF
            if key in key_map:
                selected_pose = key_map[key]
                app_state = "STANDBY"
                status_banner = f"Da chon Pose: {selected_pose} | Nhan SPACE de dem nguoc 3s va thu mau"
                banner_color = (0, 215, 255)
            elif key == ord(' '):
                if app_state == "STANDBY":
                    app_state = "COUNTDOWN"
                    countdown_start_t = time.perf_counter()
                    status_banner = f"Chuan bi the '{selected_pose}'! Bat dau dem nguoc 3 giay..."
                    banner_color = (0, 215, 255)
                else:
                    app_state = "STANDBY"
                    status_banner = "Da dung/huy qua trinh thu mau."
                    banner_color = (200, 200, 200)

            countdown_sec = None
            is_recording = False

            if app_state == "COUNTDOWN":
                elapsed = time.perf_counter() - countdown_start_t
                remaining = COUNTDOWN_DURATION - elapsed
                if remaining > 0:
                    countdown_sec = remaining
                    status_banner = f"[DEM NGUOC {int(math.ceil(remaining))}s] Hay vao tu the '{selected_pose}'!"
                    banner_color = (0, 215, 255)
                else:
                    app_state = "RECORDING"
                    status_banner = f"[BAT DAU THU MAU] Dang thu the '{selected_pose}' cho den khi du {TARGET_SAMPLES_PER_POSE} mau..."
                    banner_color = (0, 255, 0)

            if app_state == "RECORDING":
                is_recording = True

            if results.multi_hand_landmarks and results.multi_handedness:
                for lm, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                    # Lay nhan tay (Left/Right) tu MediaPipe
                    hand_label, mp_conf = get_corrected_handedness(handedness, invert_handedness=False)
                    feat = extract_hand_features(lm)

                    x, y, s, v_scale, scale_gain, v_planar = trackers[hand_label].update(
                        feat["x"], feat["y"], feat["hand_size"], ts_ms
                    )
                    feat["v_scale"] = v_scale
                    feat["scale_gain"] = scale_gain
                    feat["v_planar"] = v_planar

                    mp_draw.draw_landmarks(frame, lm, mp_hands.HAND_CONNECTIONS)
                    cx, cy = int(x * w), int(y * h)

                    is_valid, reason = validate_sample_for_pose(feat, hand_label, mp_conf, selected_pose)
                    hand_color = (0, 255, 0) if is_valid else (0, 0, 255)

                    cv2.circle(frame, (cx, cy), 7, hand_color, -1)
                    cv2.putText(frame, f"[{hand_label}] MP:{mp_conf*100:.0f}% | v_scale:{v_scale:+.2f}/s",
                                (max(10, cx - 105), max(105, cy - 28)), cv2.FONT_HERSHEY_SIMPLEX, 0.48, hand_color, 2)
                    cv2.putText(frame, f"size:{s:.2f} | gain:{scale_gain*100:+.0f}% | rOpen:{feat['r_open']:.2f}",
                                (max(10, cx - 105), max(125, cy - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (255, 255, 0), 1)

                    if is_recording:
                        cnt = len(collected[hand_label][selected_pose])
                        if is_valid:
                            if cnt < TARGET_SAMPLES_PER_POSE:
                                feat["ts"] = ts_ms
                                feat["mp_conf"] = mp_conf
                                feat["clean_frame"] = clean_frame
                                collected[hand_label][selected_pose].append(feat)
                                cnt = len(collected[hand_label][selected_pose])
                                status_banner = f"[DANG THU] {hand_label} - {selected_pose} ({cnt}/{TARGET_SAMPLES_PER_POSE} mau) | v_scale: {v_scale:+.2f}/s"
                                banner_color = (0, 255, 0)

                                if cnt >= TARGET_SAMPLES_PER_POSE:
                                    app_state = "STANDBY"
                                    is_recording = False
                                    status_banner = f"[HOAN TAT] Tay {hand_label} da thu du {TARGET_SAMPLES_PER_POSE} mau the '{selected_pose}'!"
                                    banner_color = (0, 255, 0)
                                    print(f"[*] {status_banner}")
                            else:
                                app_state = "STANDBY"
                                is_recording = False
                                status_banner = f"[DA DU MAU] Tay {hand_label} da dat {TARGET_SAMPLES_PER_POSE}/{TARGET_SAMPLES_PER_POSE} mau."
                                banner_color = (0, 255, 0)
                        else:
                            status_banner = f"[TU CHOI] {hand_label} ({cnt}/{TARGET_SAMPLES_PER_POSE}): {reason}"
                            banner_color = (0, 0, 255)

            # Phim 'c': Chup anh nhanh khung hinh hien tai
            if key == ord('c'):
                snap_dir = os.path.join(DATASET_IMAGE_DIR, "snapshots")
                os.makedirs(snap_dir, exist_ok=True)
                snap_path = os.path.join(snap_dir, f"snap_{int(time.time()*1000)}.jpg")
                cv2.imwrite(snap_path, clean_frame)
                status_banner = f"Da chup anh: {os.path.basename(snap_path)}"
                banner_color = (0, 255, 255)
                print(f"[*] {status_banner}")

            elif key == ord('r'):
                for side in ["Left", "Right"]:
                    collected[side][selected_pose].clear()
                status_banner = f"Da xoa mau tam cua Pose: {selected_pose}"
                banner_color = (0, 215, 255)

            elif key == ord('s'):
                ok, msg = save_all_data(collected, save_images=True)
                status_banner = msg
                banner_color = (0, 255, 0) if ok else (0, 0, 255)
                print(f"[*] {msg}")

            elif key == ord('q'):
                break

            draw_collection_hud(frame, selected_pose, is_recording, collected, status_banner, banner_color, fps,
                                countdown_sec=countdown_sec)
            cv2.imshow("1. Data Collection & Pose Setting (OpenCV HUD)", frame)

    finally:
        cam.release()
        hands.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
