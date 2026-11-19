"""Realtime test of MediaPipe Gesture Recognizer: stability + labeled accuracy.

Keys:
  0-7   set ground-truth gesture you are performing (see list on screen)
  SPACE start/stop recording labeled samples
  r     reset statistics
  s     save report (CSV + confusion matrix) to results/
  q/ESC quit
"""
import argparse
import csv
import time
from collections import Counter, deque
from datetime import datetime

import cv2
import numpy as np

from punchar.recognizer.mediapipe_recognizer import GESTURES, create_recognizer, draw_result, to_mp_image, top_gesture
from punchar.metrics.report import RESULTS_DIR, build_report


class Stats:
    def __init__(self, window=90):
        self.window = window
        self.reset()

    def reset(self):
        self.frames = 0
        self.detected = 0
        self.latencies = deque(maxlen=self.window)
        self.recent_labels = deque(maxlen=self.window)
        self.switches = 0
        self.prev_label = None
        self.scores = []
        self.samples = []  # (timestamp, ground_truth, predicted, score, latency_ms)

    def update(self, label, score, latency_ms, hand_found):
        self.frames += 1
        self.detected += hand_found
        self.latencies.append(latency_ms)
        self.recent_labels.append(label)
        if self.prev_label is not None and label != self.prev_label:
            self.switches += 1
        self.prev_label = label
        if hand_found:
            self.scores.append(score)

    def flicker_rate(self):
        """Fraction of label changes between consecutive frames in the recent window."""
        labels = list(self.recent_labels)
        if len(labels) < 2:
            return 0.0
        changes = sum(a != b for a, b in zip(labels, labels[1:]))
        return changes / (len(labels) - 1)

    def accuracy(self):
        if not self.samples:
            return None
        return sum(gt == pred for _, gt, pred, _, _ in self.samples) / len(self.samples)


def save_report(stats):
    if not stats.samples:
        print("No labeled samples to save.")
        return
    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    csv_path = RESULTS_DIR / f"live_{stamp}.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "ground_truth", "predicted", "score", "latency_ms"])
        writer.writerows(stats.samples)

    gts = [s[1] for s in stats.samples]
    preds = [s[2] for s in stats.samples]
    report = build_report(gts, preds)
    report += (f"\nFrames: {stats.frames}, hand detection rate: {stats.detected / max(stats.frames, 1):.1%}"
               f"\nMean latency: {np.mean([s[4] for s in stats.samples]):.1f} ms\n")
    report_path = RESULTS_DIR / f"live_{stamp}_report.txt"
    report_path.write_text(report)
    print(report)
    print(f"Saved {csv_path} and {report_path}")


def draw_panel(frame, stats, label, score, gt, recording, fps):
    lat = np.mean(stats.latencies) if stats.latencies else 0
    acc = stats.accuracy()
    lines = [
        f"FPS: {fps:5.1f}   latency: {lat:5.1f} ms",
        f"Pred: {label} ({score:.2f})",
        f"Detect rate: {stats.detected / max(stats.frames, 1):.1%}",
        f"Flicker (last {stats.window}f): {stats.flicker_rate():.1%}",
        f"Mean conf: {np.mean(stats.scores) if stats.scores else 0:.2f}",
        f"GT: {gt}   {'[REC]' if recording else '[paused]'}",
        f"Samples: {len(stats.samples)}   Acc: {'-' if acc is None else f'{acc:.1%}'}",
    ]
    cv2.rectangle(frame, (0, 0), (360, 20 + 24 * len(lines)), (0, 0, 0), -1)
    for i, text in enumerate(lines):
        color = (0, 0, 255) if recording and text.startswith("GT") else (255, 255, 255)
        cv2.putText(frame, text, (8, 22 + 24 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)

    h = frame.shape[0]
    legend = "  ".join(f"{i}:{g}" for i, g in enumerate(GESTURES))
    cv2.putText(frame, legend, (8, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 0), 1)
    cv2.putText(frame, "SPACE rec | r reset | s save | q quit", (8, h - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--num-hands", type=int, default=1)
    parser.add_argument("--det-conf", type=float, default=0.5)
    parser.add_argument("--track-conf", type=float, default=0.5)
    parser.add_argument("--no-mirror", action="store_true")
    args = parser.parse_args()

    cap = cv2.VideoCapture(args.camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    if not cap.isOpened():
        raise SystemExit(f"Cannot open camera {args.camera}")

    recognizer = create_recognizer("video", args.num_hands, args.det_conf, args.det_conf, args.track_conf)
    stats = Stats()
    gt = GESTURES[0]
    recording = False
    t0 = time.monotonic()
    last_ts = -1
    frame_times = deque(maxlen=30)

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if not args.no_mirror:
            frame = cv2.flip(frame, 1)

        # VIDEO mode requires strictly increasing timestamps
        ts = max(int((time.monotonic() - t0) * 1000), last_ts + 1)
        last_ts = ts
        start = time.perf_counter()
        result = recognizer.recognize_for_video(to_mp_image(frame), ts)
        latency_ms = (time.perf_counter() - start) * 1000

        label, score = top_gesture(result)
        stats.update(label, score, latency_ms, bool(result.hand_landmarks))
        if recording:
            stats.samples.append((ts, gt, label, round(score, 4), round(latency_ms, 2)))

        frame_times.append(time.perf_counter())
        fps = (len(frame_times) - 1) / (frame_times[-1] - frame_times[0]) if len(frame_times) > 1 else 0

        draw_result(frame, result)
        draw_panel(frame, stats, label, score, gt, recording, fps)
        cv2.imshow("MediaPipe Gesture Test", frame)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        elif ord("0") <= key < ord("0") + len(GESTURES):
            gt = GESTURES[key - ord("0")]
        elif key == ord(" "):
            recording = not recording
        elif key == ord("r"):
            stats.reset()
        elif key == ord("s"):
            save_report(stats)

    if stats.samples:
        save_report(stats)
    print(f"Label switches: {stats.switches}, gesture distribution: "
          f"{dict(Counter(stats.recent_labels))}")
    cap.release()
    cv2.destroyAllWindows()
    recognizer.close()


if __name__ == "__main__":
    main()
