"""Full pipeline: Capture -> Recognizer -> Decision Logic -> UDP to Unity.

Usage (from python/): python -m punchar.main [--config path.toml]
"""
import argparse
import time

from punchar.capture import Camera
from punchar.config import load_config
from punchar.decision import DecisionLogic
from punchar.metrics import StageTimer
from punchar.paths import CONFIG_PATH
from punchar.recognizer import create_from_config
from punchar.transport import FrameSender, UdpSender


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=CONFIG_PATH)
    parser.add_argument("--camera", type=int, default=None, help="Camera index override (e.g. 0, 1, 2)")
    args = parser.parse_args()
    cfg = load_config(args.config)
    if args.camera is not None:
        cfg["capture"]["camera"] = args.camera

    camera = Camera(**cfg["capture"]).start()
    recognizer = create_from_config(cfg)
    recognizer.load()
    decision = DecisionLogic(cfg["decision"])
    sender = UdpSender(**cfg["transport"])
    timer = StageTimer()
    vcfg = dict(cfg.get("video", {}))
    video = FrameSender(timer=timer, **vcfg) if vcfg.pop("enabled", False) else None

    print(f"Sending to {sender.addr}" + (f", video to {video.addr}" if video else "") + ". Ctrl+C to stop.")
    try:
        while True:
            frame = camera.read()
            if frame is None:
                time.sleep(0.001)
                continue
            with timer.stage("recognize"):
                result = recognizer.predict(frame.image, frame.frame_id, frame.timestamp_ms)
            with timer.stage("decision"):
                events = decision.update(result)
            with timer.stage("send"):
                sender.send_pose(result)
                for ev in events:
                    sender.send_strike(ev)
                for side in getattr(decision, "lost_hands", []):
                    sender.send_hand_lost(result.timestamp_ms, side)
                if video:  # after pose, so the background frame matches the hand pose
                    video.submit(frame.image, frame.frame_id, frame.timestamp_ms)
            timer.add("since_capture", time.time_ns() / 1e6 - frame.timestamp_ms)
    except KeyboardInterrupt:
        pass
    finally:
        camera.stop()
        recognizer.close()
        sender.close()
        if video:
            video.close()
        print(timer.summary())


if __name__ == "__main__":
    main()
