using UnityEngine;
using UnityEngine.InputSystem;

// Feeds strikes into StrikeJudge from two sources:
//   1. UDP "strike" messages from Python (via UdpReceiver)
//   2. Keyboard, as a fallback for development without webcam:
//        F / J = PUNCH_STRAIGHT left / right
//        D / K = BLOCK          left / right
//        S / L = OPEN_PALM      left / right
// Both go through the same OnStrike(hand, kind).
// Reads receiver.Messages itself, so do not put another reader (e.g. PoseSpheres) in the same scene.
public class GameManager : MonoBehaviour
{
    public UdpReceiver receiver;
    public StrikeJudge judge;
    public bool keyboardStrikes = true;

    void Update()
    {
        while (receiver != null && receiver.Messages.TryDequeue(out string json))
        {
            var msg = JsonUtility.FromJson<BaseMessage>(json);
            switch (msg.type)
            {
                case "strike":
                    var s = JsonUtility.FromJson<StrikeMessage>(json);
                    OnStrike(s.hand, s.kind);
                    break;
                case "pose":
                    // 3D hands: Duy (Assets/_Project/Hands/)
                    break;
                case "hand_lost":
                    break;
                // unknown type: ignore (data contract)
            }
        }

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
