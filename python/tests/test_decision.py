"""Decision logic tests with synthetic FrameResult sequences. Run: python -m pytest tests/"""
from punchar.config import load_config
from punchar.decision import DecisionLogic
from punchar.recognizer.base import FrameResult, HandResult


def make_hand(handedness="Left", shape="Closed_Fist", size=0.1, score=0.9, x=0.5, y=0.5):
    """Fake hand whose wrist->middle-MCP distance equals `size`."""
    lms = [(x, y, 0.0)] * 21
    lms[0] = (x, y, 0.0)
    lms[9] = (x, y - size, 0.0)
    return HandResult(handedness, shape, score, lms, lms)


def test_no_hands_no_events():
    logic = DecisionLogic(load_config()["decision"])
    assert logic.update(FrameResult(0, 0, [])) == []


def test_idle_fist_does_not_strike():
    logic = DecisionLogic(load_config()["decision"])
    for i in range(10):
        # Stationary fist held less than block_hold_ms or moving around
        # Here size=0.10, but at 0..10 * 10 ms (total 90ms < block_hold_ms 120ms)
        assert logic.update(FrameResult(i, i * 10, [make_hand(size=0.1)])) == []


def test_fast_growing_fist_emits_punch():
    logic = DecisionLogic(load_config()["decision"])
    events = []
    # Frame 0: small fist at t=0
    events.extend(logic.update(FrameResult(0, 0, [make_hand(size=0.10)])))
    # Frame 1: fist growing at t=33 (growth > 15%)
    events.extend(logic.update(FrameResult(1, 33, [make_hand(size=0.15)])))
    punches = [e for e in events if e.kind == "PUNCH_STRAIGHT"]
    assert len(punches) == 1
    assert punches[0].hand == "Left"


def test_open_palm_push_emits_strike():
    logic = DecisionLogic(load_config()["decision"])
    events = []
    # Frame 0: palm at t=0
    events.extend(logic.update(FrameResult(0, 0, [make_hand(shape="Open_Palm", size=0.10)])))
    # Frame 1: pushing palm at t=40
    events.extend(logic.update(FrameResult(1, 40, [make_hand(shape="Open_Palm", size=0.15)])))
    palms = [e for e in events if e.kind == "OPEN_PALM"]
    assert len(palms) == 1
    assert palms[0].hand == "Left"


def test_cooldown_blocks_immediate_repeat():
    logic = DecisionLogic(load_config()["decision"])
    events1 = []
    events1.extend(logic.update(FrameResult(0, 0, [make_hand(size=0.10)])))
    events1.extend(logic.update(FrameResult(1, 40, [make_hand(size=0.16)])))
    assert len([e for e in events1 if e.kind == "PUNCH_STRAIGHT"]) == 1

    # Immediately in cooldown (t=70 < cooldown 250ms)
    events2 = logic.update(FrameResult(2, 70, [make_hand(size=0.25)]))
    assert len(events2) == 0


def test_block_held_fist_emits_block():
    logic = DecisionLogic(load_config()["decision"])
    events = []
    # Hold stationary fist for 200ms (> block_hold_ms 120ms)
    for i in range(8):
        t_ms = i * 30
        ev = logic.update(FrameResult(i, t_ms, [make_hand(size=0.10)]))
        events.extend(ev)

    block_events = [e for e in events if e.kind == "BLOCK"]
    assert len(block_events) == 1
    assert block_events[0].kind == "BLOCK"


def test_get_corrected_handedness():
    from punchar.decision.features import get_corrected_handedness

    # String input
    assert get_corrected_handedness("Left", 0.9) == ("Left", 0.9)
    assert get_corrected_handedness("Left", 0.9, invert=True) == ("Right", 0.9)
    assert get_corrected_handedness("Right", 0.8, invert_handedness=True) == ("Left", 0.8)

    # MediaPipe Classification mock
    class MockClassification:
        label = "Left"
        score = 0.95

    class MockHandedness:
        classification = [MockClassification()]

    label, score = get_corrected_handedness(MockHandedness(), invert_handedness=False)
    assert label == "Left" and score == 0.95

    label_inv, _ = get_corrected_handedness(MockHandedness(), invert_handedness=True)
    assert label_inv == "Right"

