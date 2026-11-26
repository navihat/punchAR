using UnityEngine;

// Sandbox check for the Python -> Unity pipeline: moves one object per hand to the
// palm position from "pose" messages. Hides a hand when it is missing from the latest pose.
public class PoseSpheres : MonoBehaviour
{
    public UdpReceiver receiver;
    public Camera cam;
    public Transform leftHand;
    public Transform rightHand;
    public float depth = 2f;   // distance from camera, in world units

    void OnEnable()
    {
        if (receiver == null) receiver = FindFirstObjectByType<UdpReceiver>();
        if (receiver != null) receiver.OnPoseReceived += HandlePose;
    }

    void OnDisable()
    {
        if (receiver != null) receiver.OnPoseReceived -= HandlePose;
    }

    void HandlePose(PoseMessage latest)
    {
        if (latest == null || cam == null) return;

        bool seenLeft = false, seenRight = false;
        foreach (var h in latest.hands)
        {
            Transform target = h.hand == "Left" ? leftHand : h.hand == "Right" ? rightHand : null;
            if (target == null) continue;
            target.position = cam.ViewportToWorldPoint(new Vector3(h.x, h.y, depth));
            if (target == leftHand) seenLeft = true; else seenRight = true;
        }
        if (leftHand != null) leftHand.gameObject.SetActive(seenLeft);
        if (rightHand != null) rightHand.gameObject.SetActive(seenRight);
    }
}
