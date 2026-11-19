"""Decision logic tests with synthetic FrameResult sequences. Run: python -m pytest tests/"""
from punchar.config import load_config
from punchar.decision import DecisionLogic
from punchar.recognizer.base import FrameResult, HandResult


def make_hand(handedness="Left", shape="Closed_Fist", size=0.1, score=0.9):
    """Fake hand whose wrist->middle-MCP distance equals `size`."""
    lms = [(0.5, 0.5, 0.0)] * 21
    lms[9] = (0.5, 0.5 - size, 0.0)
    return HandResult(handedness, shape, score, lms, lms)


def test_no_hands_no_events():
    logic = DecisionLogic(load_config()["decision"])
    assert logic.update(FrameResult(0, 0, [])) == []


def test_idle_fist_does_not_strike():
    logic = DecisionLogic(load_config()["decision"])
    for i in range(10):
        assert logic.update(FrameResult(i, i * 33, [make_hand()])) == []


# TODO: test_fast_growing_fist_emits_punch, test_cooldown, test_brief_tracking_loss
