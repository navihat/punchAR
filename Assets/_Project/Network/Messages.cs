using System;

// Message format = contract with Python (docs/team/PHAN_CONG.vi.md, "Hợp đồng dữ liệu Python → Unity").
// Do not change alone: update python/punchar/transport/udp_sender.py in the same PR.
// Parse with JsonUtility.FromJson<...>(json) after checking "type"; ignore unknown types.
// t = capture time, Unix epoch ms. x, y = 0..1 viewport of the mirrored webcam image (y up).

[Serializable]
public class BaseMessage { public string type; public long t; }

[Serializable]
public class HandPose
{
    public string hand;   // "Left" | "Right", player's real hand
    public float x;       // palm center (landmark 9)
    public float y;
    public float size;    // wrist -> landmark 9 distance, bigger = closer to camera
    public string shape;  // Closed_Fist, Open_Palm, ..., None
    public float score;
    public float[] lm;    // 21 landmarks flattened: x0,y0,z0, ..., x20,y20,z20 (z < 0 = closer)
}

[Serializable]
public class PoseMessage { public string type; public long t; public int frame; public HandPose[] hands; }

[Serializable]
public class StrikeMessage { public string type; public long t; public string hand; public string kind; public float x; public float y; }

[Serializable]
public class HandLostMessage { public string type; public long t; public string hand; }
