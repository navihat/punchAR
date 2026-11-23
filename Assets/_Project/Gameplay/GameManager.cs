using UnityEngine;
using UnityEngine.InputSystem;

// Feeds strikes into StrikeJudge from two sources:
//   1. UDP "strike" messages from Python (via UdpReceiver event)
//   2. Keyboard, as a fallback for development without webcam:
//        F / J = PUNCH_STRAIGHT left / right
//        D / K = BLOCK          left / right
//        S / L = OPEN_PALM      left / right
// Both go through the same OnStrike(hand, kind).
public class GameManager : MonoBehaviour
{
    public UdpReceiver receiver;
    public StrikeJudge judge;
    public bool keyboardStrikes = true;

    void OnEnable()
    {
        if (receiver == null) receiver = FindFirstObjectByType<UdpReceiver>();
        if (receiver != null) receiver.OnStrikeReceived += HandleStrike;
    }

    void OnDisable()
    {
        if (receiver != null) receiver.OnStrikeReceived -= HandleStrike;
    }

    void HandleStrike(StrikeMessage s)
    {
        OnStrike(s.hand, s.kind);
    }

    void Update()
    {
        if (keyboardStrikes) ReadKeyboard();
    }

    void ReadKeyboard()
    {
        var kb = Keyboard.current;
        if (kb == null) return;
        if (kb.fKey.wasPressedThisFrame) OnStrike(StrikeKinds.Left, StrikeKinds.PunchStraight);
        if (kb.jKey.wasPressedThisFrame) OnStrike(StrikeKinds.Right, StrikeKinds.PunchStraight);
        if (kb.dKey.wasPressedThisFrame) OnStrike(StrikeKinds.Left, StrikeKinds.Block);
        if (kb.kKey.wasPressedThisFrame) OnStrike(StrikeKinds.Right, StrikeKinds.Block);
        if (kb.sKey.wasPressedThisFrame) OnStrike(StrikeKinds.Left, StrikeKinds.OpenPalm);
        if (kb.lKey.wasPressedThisFrame) OnStrike(StrikeKinds.Right, StrikeKinds.OpenPalm);
    }

    // Single entry point for every strike source.
    public void OnStrike(string hand, string kind)
    {
        if (judge != null) judge.OnStrike(hand, kind);
        else Debug.Log($"Strike {hand} {kind} (no StrikeJudge assigned)");
    }
}
