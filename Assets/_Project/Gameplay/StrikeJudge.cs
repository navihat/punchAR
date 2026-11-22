using System;
using UnityEngine;

public enum StrikeResult
{
    Hit,         // right hand, right kind, target inside hit zone
    WrongKind,   // right hand, target in zone, but wrong strike kind
    WrongHand,   // nothing in this hand's zone, but a target waits on the other side
    Ignored,     // no target in either zone: strike does nothing
    Miss,        // a target flew past the hit zone without a correct strike
}

// Hit/miss rules. Every strike source (keyboard, UDP "strike" message) calls OnStrike(hand, kind);
// this is the single place that decides the result.
public class StrikeJudge : MonoBehaviour
{
    [Header("Hit zone (world Z, camera looks toward +Z)")]
    public float hitZoneNearZ = 1.5f;   // past this = miss
    public float hitZoneFarZ = 3.0f;    // closer than this = can be hit

    [Tooltip("Wrong kind / wrong hand breaks the combo. Off = such strikes do nothing.")]
    public bool penalizeWrongStrike = true;

    public ScoreKeeper score;

    // (result, hand, kind) for HUD, sound, effects.
    public event Action<StrikeResult, string, string> Judged;

    public StrikeResult OnStrike(string hand, string kind)
    {
        Target own = NearestInZone(hand);
        StrikeResult result;
        if (own != null)
        {
            if (own.Kind == kind) { own.Break(); result = StrikeResult.Hit; }
            else result = StrikeResult.WrongKind;
        }
        else
        {
            string other = hand == StrikeKinds.Left ? StrikeKinds.Right : StrikeKinds.Left;
            result = NearestInZone(other) != null ? StrikeResult.WrongHand : StrikeResult.Ignored;
        }

        if (!penalizeWrongStrike && (result == StrikeResult.WrongKind || result == StrikeResult.WrongHand))
            result = StrikeResult.Ignored;

        Apply(result, hand, kind);
        return result;
    }

    public void ReportMiss(Target t) => Apply(StrikeResult.Miss, t.Hand, t.Kind);

    void Apply(StrikeResult result, string hand, string kind)
    {
        if (score != null) score.Register(result);
        Debug.Log($"[StrikeJudge] {result} {hand} {kind}");
        Judged?.Invoke(result, hand, kind);
    }

    // Target of this hand inside the hit zone, closest to the camera (the one about to be missed).
    Target NearestInZone(string hand)
    {
        Target best = null;
        foreach (var t in Target.Active)
        {
            if (t.Resolved || t.Hand != hand) continue;
            float z = t.transform.position.z;
            if (z < hitZoneNearZ || z > hitZoneFarZ) continue;
            if (best == null || z < best.transform.position.z) best = t;
        }
        return best;
    }
}
