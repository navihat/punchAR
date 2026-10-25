"""Shared helpers: load MediaPipe Gesture Recognizer and draw results."""
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python import vision

ROOT_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT_DIR / "models" / "gesture_recognizer.task"

# Canned gestures of the official MediaPipe model
GESTURES = [
    "None",
    "Closed_Fist",
    "Open_Palm",
    "Pointing_Up",
    "Thumb_Down",
    "Thumb_Up",
    "Victory",
    "ILoveYou",
]

HAND_CONNECTIONS = [(c.start, c.end) for c in vision.HandLandmarksConnections.HAND_CONNECTIONS]


def create_recognizer(mode="video", num_hands=1, det_conf=0.5, presence_conf=0.5, track_conf=0.5):
    running_mode = vision.RunningMode.VIDEO if mode == "video" else vision.RunningMode.IMAGE
    options = vision.GestureRecognizerOptions(
        base_options=BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=running_mode,
        num_hands=num_hands,
        min_hand_detection_confidence=det_conf,
        min_hand_presence_confidence=presence_conf,
        min_tracking_confidence=track_conf,
    )
    return vision.GestureRecognizer.create_from_options(options)


def to_mp_image(bgr):
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    return mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)


def top_gesture(result, hand_idx=0):
    """Return (label, score) of the top gesture for a hand, or ("None", 0.0) if no hand."""
    if not result.gestures or len(result.gestures) <= hand_idx:
        return "None", 0.0
    cat = result.gestures[hand_idx][0]
    return cat.category_name or "None", cat.score


def draw_result(frame, result):
    h, w = frame.shape[:2]
    for i, landmarks in enumerate(result.hand_landmarks):
        pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
        for a, b in HAND_CONNECTIONS:
            cv2.line(frame, pts[a], pts[b], (255, 255, 255), 2)
        for p in pts:
            cv2.circle(frame, p, 4, (0, 140, 255), -1)

        label, score = top_gesture(result, i)
        handed = result.handedness[i][0].category_name if result.handedness else "?"
        x0 = min(p[0] for p in pts)
        y0 = max(min(p[1] for p in pts) - 10, 20)
        cv2.putText(frame, f"{handed}: {label} {score:.2f}", (x0, y0),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
