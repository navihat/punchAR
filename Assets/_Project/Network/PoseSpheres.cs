using UnityEngine;

// Sandbox check for the Python -> Unity pipeline: moves one object per hand to the
// palm position from "pose" messages. Hides a hand when it is missing from the latest pose.
// Reads receiver.Messages itself, so do not put another reader (e.g. GameManager) in the same scene.
public class PoseSpheres : MonoBehaviour
{
    public UdpReceiver receiver;
    public Camera cam;
    public Transform leftHand;
    public Transform rightHand;
    public float depth = 2f;   // distance from camera, in world units

    void Update()
    {
        PoseMessage latest = null;
        while (receiver.Messages.TryDequeue(out string json))
        {
            if (JsonUtility.FromJson<BaseMessage>(json).type == "pose")
                latest = JsonUtility.FromJson<PoseMessage>(json);
        }
        if (latest == null) return;   // no new pose this frame, keep last positions

        bool seenLeft = false, seenRight = false;
        foreach (var h in latest.hands)
        {
            Transform target = h.hand == "Left" ? leftHand : h.hand == "Right" ? rightHand : null;
            if (target == null) continue;
            target.position = cam.ViewportToWorldPoint(new Vector3(h.x, h.y, depth));
            if (target == leftHand) seenLeft = true; else seenRight = true;
        }
        leftHand.gameObject.SetActive(seenLeft);
        rightHand.gameObject.SetActive(seenRight);
    }
}
