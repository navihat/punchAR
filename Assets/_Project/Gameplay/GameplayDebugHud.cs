using UnityEngine;

// Temporary on-screen text (IMGUI) for score, combo and the last strike result.
// Will be replaced by real UI in Assets/_Project/UI/.
public class GameplayDebugHud : MonoBehaviour
{
    public ScoreKeeper score;
    public StrikeJudge judge;

    string last = "-";
    float lastTime = -10f;
    GUIStyle style;

    void OnEnable() { if (judge != null) judge.Judged += OnJudged; }
    void OnDisable() { if (judge != null) judge.Judged -= OnJudged; }

    void OnJudged(StrikeResult r, string hand, string kind)
    {
        if (r == StrikeResult.Ignored) return;
        last = $"{r}  ({hand} {kind})";
        lastTime = Time.time;
    }

    void OnGUI()
    {
        if (score == null) return;
        style ??= new GUIStyle(GUI.skin.label) { fontSize = 22 };
        GUILayout.BeginArea(new Rect(16, 16, 600, 260));
        GUILayout.Label($"Score {score.Score}   Combo {score.Combo}  x{score.Multiplier}", style);
        GUILayout.Label($"Hit {score.Hits}   Miss {score.Misses}   Wrong {score.WrongStrikes}   Hit rate {score.HitRate:P0}", style);
        if (Time.time - lastTime < 1f) GUILayout.Label(last, style);
        GUILayout.Label("Keys: F/J punch  D/K block  S/L open palm (left/right)", style);
        GUILayout.EndArea();
    }
}
