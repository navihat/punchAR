using UnityEngine;

// Score and combo. Hit: +basePoints × multiplier, combo +1.
// Miss / wrong kind / wrong hand: combo back to 0. Multiplier grows every comboStep hits.
public class ScoreKeeper : MonoBehaviour
{
    public int basePoints = 100;
    public int comboStep = 5;        // multiplier +1 every 5 hits in a row
    public int maxMultiplier = 4;

    public int Score { get; private set; }
    public int Combo { get; private set; }
    public int BestCombo { get; private set; }
    public int Hits { get; private set; }
    public int Misses { get; private set; }     // targets that flew past
    public int WrongStrikes { get; private set; }

    public int Multiplier => Mathf.Min(1 + Combo / comboStep, maxMultiplier);

    // Share of targets broken (hits / (hits + misses)), shared metric with Thái and Duy.
    public float HitRate => Hits + Misses == 0 ? 0f : (float)Hits / (Hits + Misses);

    public void Register(StrikeResult r)
    {
        switch (r)
        {
            case StrikeResult.Hit:
                Score += basePoints * Multiplier;
                Combo++;
                Hits++;
                if (Combo > BestCombo) BestCombo = Combo;
                break;
            case StrikeResult.Miss:
                Misses++;
                Combo = 0;
                break;
            case StrikeResult.WrongKind:
            case StrikeResult.WrongHand:
                WrongStrikes++;
                Combo = 0;
                break;
        }
    }

    public void ResetAll()
    {
        Score = Combo = BestCombo = Hits = Misses = WrongStrikes = 0;
    }
}
