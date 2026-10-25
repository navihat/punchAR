"""Offline accuracy evaluation on a labeled image folder.

Expected layout (folder name = ground-truth label, must match MediaPipe gesture names):
  dataset/
    Thumb_Up/    img1.jpg ...
    Open_Palm/   ...
    None/        ...   (images with no hand / unknown gesture)

Usage: python -m tools.eval_dataset dataset/
"""
import argparse
import csv
import time
from datetime import datetime
from pathlib import Path

import cv2

from punchar.recognizer.mediapipe_recognizer import GESTURES, create_recognizer, to_mp_image, top_gesture
from punchar.metrics.report import RESULTS_DIR, build_report

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--det-conf", type=float, default=0.5)
    args = parser.parse_args()

    recognizer = create_recognizer("image", det_conf=args.det_conf)
    rows, gts, preds, latencies = [], [], [], []
    no_hand = 0

    for class_dir in sorted(p for p in args.dataset.iterdir() if p.is_dir()):
        if class_dir.name not in GESTURES:
            print(f"Skipping '{class_dir.name}' (not one of {GESTURES})")
            continue
        for img_path in sorted(class_dir.iterdir()):
            if img_path.suffix.lower() not in IMAGE_EXTS:
                continue
            img = cv2.imread(str(img_path))
            if img is None:
                print(f"Cannot read {img_path}")
                continue
            start = time.perf_counter()
            result = recognizer.recognize(to_mp_image(img))
            latency_ms = (time.perf_counter() - start) * 1000
            label, score = top_gesture(result)
            no_hand += not result.hand_landmarks

            gts.append(class_dir.name)
            preds.append(label)
            latencies.append(latency_ms)
            rows.append((str(img_path), class_dir.name, label, round(score, 4), round(latency_ms, 2)))

    recognizer.close()
    if not rows:
        raise SystemExit("No images found.")

    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = RESULTS_DIR / f"dataset_{stamp}.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["image", "ground_truth", "predicted", "score", "latency_ms"])
        writer.writerows(rows)

    report = build_report(gts, preds)
    report += (f"\nImages with no hand detected: {no_hand}/{len(rows)}"
               f"\nMean latency: {sum(latencies) / len(latencies):.1f} ms\n")
    report_path = RESULTS_DIR / f"dataset_{stamp}_report.txt"
    report_path.write_text(report)
    print(report)
    print(f"Saved {csv_path} and {report_path}")


if __name__ == "__main__":
    main()
