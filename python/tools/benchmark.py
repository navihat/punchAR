"""Benchmark the pipeline on recorded videos (not live webcam) -> p50/p95/p99, FPS, CPU%.

Usage (from python/): python -m tools.benchmark data/videos/clip.mp4
Weak-device simulation: taskset -c 0 python -m tools.benchmark ...
"""
import argparse
from pathlib import Path

import cv2

from punchar.config import load_config
from punchar.decision import DecisionLogic
from punchar.metrics import StageTimer
from punchar.recognizer import create_from_config


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("videos", nargs="+", type=Path)
    args = parser.parse_args()
    cfg = load_config()

    for video in args.videos:
        cap = cv2.VideoCapture(str(video))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        recognizer = create_from_config(cfg)
        recognizer.load()
        decision = DecisionLogic(cfg["decision"])
        timer = StageTimer()
        frame_id = 0
        while True:
            ok, img = cap.read()
            if not ok:
                break
            ts = int(frame_id * 1000 / fps)  # video time, so results are reproducible
            with timer.stage("recognize"):
                result = recognizer.predict(img, frame_id, ts)
            with timer.stage("decision"):
                decision.update(result)
            frame_id += 1
        recognizer.close()
        cap.release()
        print(f"== {video} ({frame_id} frames)\n{timer.summary()}\n")
        # TODO: CPU%/RAM (psutil?), strike-level accuracy vs. labels, save to results/


if __name__ == "__main__":
    main()
