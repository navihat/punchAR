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
from punchar.transport import UdpSender


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=CONFIG_PATH)
    args = parser.parse_args()
    cfg = load_config(args.config)

    camera = Camera(**cfg["capture"]).start()
    recognizer = create_from_config(cfg)
    recognizer.load()
    decision = DecisionLogic(cfg["decision"])
    sender = UdpSender(**cfg["transport"])
    timer = StageTimer()

    print(f"Sending to {sender.addr}. Ctrl+C to stop.")
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
            timer.add("since_capture", time.monotonic() * 1000 - frame.timestamp_ms)
    except KeyboardInterrupt:
        pass
    finally:
        camera.stop()
        recognizer.close()
        sender.close()
        print(timer.summary())


if __name__ == "__main__":
    main()
