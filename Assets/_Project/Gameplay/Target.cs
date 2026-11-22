using System.Collections.Generic;
using UnityEngine;

// A shape flying toward the camera along -Z. Belongs to one side (hand) and needs one strike kind.
// The spawner sets it up; StrikeJudge decides hits; the target reports a miss itself
// when it flies past the near edge of the hit zone.
public class Target : MonoBehaviour
{
    // All targets currently flying, so StrikeJudge can search them without physics.
    public static readonly List<Target> Active = new List<Target>();

    public string Hand { get; private set; }   // "Left" | "Right"
    public string Kind { get; private set; }   // StrikeKinds.*
    public bool Resolved { get; private set; }

    float speed;      // world units per second
    float missZ;      // z where the target counts as missed
    StrikeJudge judge;

    public void Init(string hand, string kind, float speed, float missZ, StrikeJudge judge)
    {
        Hand = hand;
        Kind = kind;
        this.speed = speed;
        this.missZ = missZ;
        this.judge = judge;
    }

    void OnEnable() => Active.Add(this);
    void OnDisable() => Active.Remove(this);

    void Update()
    {
        if (Resolved) return;
        transform.position += Vector3.back * (speed * Time.deltaTime);
        if (transform.position.z < missZ)
        {
            Resolved = true;
            if (judge != null) judge.ReportMiss(this);
            Destroy(gameObject);
        }
    }

    // Called by StrikeJudge on a correct strike.
    public void Break()
    {
        if (Resolved) return;
        Resolved = true;
        // TODO (Duy, Targets/): replace with break effect from the target prefab.
        Destroy(gameObject);
    }
}
