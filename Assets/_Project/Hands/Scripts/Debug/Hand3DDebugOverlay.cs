using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

namespace PunchAR.Hand3D
{
    public class Hand3DDebugOverlay : MonoBehaviour
    {
        [SerializeField] private MonoBehaviour providerSource;
        [SerializeField] private Hand3DVisualizer visualizer;
        [SerializeField] private bool showHud = true;
        [SerializeField] private bool drawSceneSkeleton = true;
        [SerializeField] private float hudScale = 1.25f;
        [SerializeField] private float worldSkeletonScale = 2.0f;

        private IHandInputProvider _provider;
        private string _lastStrikeText = "None";
        private float _fpsSmoothed = 60f;

        private static readonly int[,] BonePairs =
        {
            {0,1},{1,2},{2,3},{3,4},
            {0,5},{5,6},{6,7},{7,8},
            {0,9},{9,10},{10,11},{11,12},
            {0,13},{13,14},{14,15},{15,16},
            {0,17},{17,18},{18,19},{19,20},
            {5,9},{9,13},{13,17}
        };

        private void Awake()
        {
            _provider = providerSource as IHandInputProvider ?? GetComponent<IHandInputProvider>();
            if (visualizer == null) visualizer = GetComponent<Hand3DVisualizer>();
        }

        private void OnEnable()
        {
            if (_provider != null) _provider.OnStrikeDetected += HandleStrike;
        }

        private void OnDisable()
        {
            if (_provider != null) _provider.OnStrikeDetected -= HandleStrike;
        }

        private void HandleStrike(string hand, string kind, Vector2 pos, long tsMs)
        {
            _lastStrikeText = $"{hand} -> {kind} ({pos.x:F2}, {pos.y:F2})";
        }

        private bool IsToggleKeyPressed()
        {
#if ENABLE_INPUT_SYSTEM
            return Keyboard.current != null && Keyboard.current.f1Key.wasPressedThisFrame;
#else
            return Input.GetKeyDown(KeyCode.F1);
#endif
        }

        private void Update()
        {
            if (IsToggleKeyPressed()) showHud = !showHud;

            float currentFps = 1f / Mathf.Max(Time.unscaledDeltaTime, 0.0001f);
            _fpsSmoothed = Mathf.Lerp(_fpsSmoothed, currentFps, 0.1f);

            if (drawSceneSkeleton && _provider != null && visualizer != null)
            {
                DrawHandSkeleton(_provider.LeftHand, Color.cyan);
                DrawHandSkeleton(_provider.RightHand, Color.yellow);
            }
        }

        private void DrawHandSkeleton(HandFrameData hand, Color color)
        {
            if (!hand.isTracked || !hand.hasLandmarks || hand.landmarks == null) return;

            Vector3 palmAnchor = visualizer.MapNormalizedToWorld(hand.palmPos.x, hand.palmPos.y, 0f);
            Vector3 p9Local = Hand3DVisualizer.ToUnityHandSpace(hand.landmarks[9]);

            for (int i = 0; i < BonePairs.GetLength(0); i++)
            {
                Vector3 a = Hand3DVisualizer.ToUnityHandSpace(hand.landmarks[BonePairs[i, 0]]) - p9Local;
                Vector3 b = Hand3DVisualizer.ToUnityHandSpace(hand.landmarks[BonePairs[i, 1]]) - p9Local;

                Debug.DrawLine(palmAnchor + a * worldSkeletonScale, palmAnchor + b * worldSkeletonScale, color);
            }
        }

        private void OnGUI()
        {
            if (!showHud || _provider == null) return;

            Matrix4x4 oldMatrix = GUI.matrix;
            float scale = Mathf.Max(1f, (Screen.height / 1080f) * hudScale);
            GUI.matrix = Matrix4x4.TRS(Vector3.zero, Quaternion.identity, new Vector3(scale, scale, 1f));

            float boxWidth = 430f;
            float boxX = (Screen.width / scale) - boxWidth - 16f;

            GUI.Box(new Rect(boxX, 16f, boxWidth, 145f), "PunchAR — Hand 3D Debug HUD (F1 to Toggle)");
            GUI.Label(new Rect(boxX + 12f, 42f, 410f, 22f), $"Unity FPS: {_fpsSmoothed:F1} | UDP Rate: {_provider.PacketsPerSecond:F1} pkt/s | Latency: {_provider.LastLatencyMs} ms");
            GUI.Label(new Rect(boxX + 12f, 66f, 410f, 22f), FormatHandLine("LEFT ", _provider.LeftHand));
            GUI.Label(new Rect(boxX + 12f, 90f, 410f, 22f), FormatHandLine("RIGHT", _provider.RightHand));
            GUI.Label(new Rect(boxX + 12f, 116f, 410f, 22f), $"Last Strike: {_lastStrikeText}");

            GUI.matrix = oldMatrix;
        }

        private string FormatHandLine(string label, HandFrameData h)
        {
            if (!h.isTracked) return $"{label}: [LOST]";
            string lmTag = h.hasLandmarks ? "3D-21LM" : "Shape-Fallback";
            return $"{label}: {h.shape} | Pos({h.palmPos.x:F2},{h.palmPos.y:F2}) | {lmTag}";
        }
    }
}