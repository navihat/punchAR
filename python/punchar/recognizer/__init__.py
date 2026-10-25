from punchar.recognizer.base import FrameResult, HandResult, Recognizer
from punchar.recognizer.replay_recognizer import ReplayRecognizer


def create_from_config(cfg: dict) -> Recognizer:
    rcfg = cfg["recognizer"]
    if rcfg["type"] == "mediapipe":
        from punchar.recognizer.mediapipe_recognizer import MediaPipeRecognizer
        return MediaPipeRecognizer(rcfg["num_hands"], rcfg["det_conf"],
                                   rcfg["presence_conf"], rcfg["track_conf"])
    if rcfg["type"] == "replay":
        return ReplayRecognizer(rcfg["path"])
    raise ValueError(f"Unknown recognizer type: {rcfg['type']}")


__all__ = ["FrameResult", "HandResult", "Recognizer", "ReplayRecognizer", "create_from_config"]
