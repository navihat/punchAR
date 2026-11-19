using UnityEngine;

// Reads messages and drives the game. Keyboard keys emit fake strikes for development.
public class GameManager : MonoBehaviour
{
    public UdpReceiver receiver;

    void Update()
    {
        while (receiver != null && receiver.Messages.TryDequeue(out string json))
        {
            var msg = JsonUtility.FromJson<BaseMessage>(json);
            switch (msg.type)
            {
                case "pose":
                    // TODO: move 3D hands
                    break;
                case "strike":
                    OnStrike(JsonUtility.FromJson<StrikeMessage>(json));
                    break;
                case "hand_lost":
                    // TODO: hide hand
                    break;
            }
        }

        // Fake input (no recognizer needed)
        if (Input.GetKeyDown(KeyCode.F)) OnStrike(new StrikeMessage { hand = "Left", kind = "PUNCH_STRAIGHT" });
        if (Input.GetKeyDown(KeyCode.J)) OnStrike(new StrikeMessage { hand = "Right", kind = "PUNCH_STRAIGHT" });
    }

    void OnStrike(StrikeMessage s)
    {
        // TODO: hit check against shapes in the hit zone, score, combo
        Debug.Log($"Strike {s.hand} {s.kind}");
    }
}
