using System;
using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

namespace PunchAR.Hand3D
{
    /// <summary>
    /// Nguồn giả lập trong Unity Editor (không cần Python/Webcam).
    /// Phím: Space (Đổi Nắm/Xoè) | Q/E (Đấm thẳng Trái/Phải) | A/D (Xoè đẩy Trái/Phải)
    /// </summary>
    public class MockHandProvider : MonoBehaviour, IHandInputProvider
    {
        [SerializeField] private bool animateHands = true;
        [SerializeField] private bool startAsFist = false;

        private HandFrameData _leftHand;
        private HandFrameData _rightHand;
        private bool _isFist;

        public HandFrameData LeftHand => _leftHand;
        public HandFrameData RightHand => _rightHand;
        public long LastLatencyMs => 0;
        public float PacketsPerSecond => 60f;
        public event Action<string, string, Vector2, long> OnStrikeDetected;

        private void Awake()
        {
            _isFist = startAsFist;
            _leftHand = new HandFrameData { isTracked = true, hand = "Left", landmarks = new Vector3[21] };
            _rightHand = new HandFrameData { isTracked = true, hand = "Right", landmarks = new Vector3[21] };
        }

        private void Update()
        {
            if (WasSpacePressed()) _isFist = !_isFist;

            long nowMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
            float t = Time.time;

            string shape = _isFist ? "Closed_Fist" : "Open_Palm";
            float lx = animateHands ? 0.28f + 0.08f * Mathf.Sin(t * 2f) : 0.30f;
            float ly = animateHands ? 0.50f + 0.10f * Mathf.Cos(t * 2f) : 0.50f;
            float rx = animateHands ? 0.72f + 0.08f * Mathf.Cos(t * 2f) : 0.70f;
            float ry = animateHands ? 0.50f + 0.10f * Mathf.Sin(t * 2f) : 0.50f;

            _leftHand.isTracked = true;
            _leftHand.palmPos = new Vector2(lx, ly);
            _leftHand.shape = shape;
            _leftHand.hasLandmarks = false;
            _leftHand.receivedAtMs = nowMs;

            _rightHand.isTracked = true;
            _rightHand.palmPos = new Vector2(rx, ry);
            _rightHand.shape = shape;
            _rightHand.hasLandmarks = false;
            _rightHand.receivedAtMs = nowMs;

            if (WasKeyPressed(KeyCode.Q)) OnStrikeDetected?.Invoke("Left", "PUNCH_STRAIGHT", _leftHand.palmPos, nowMs);
            if (WasKeyPressed(KeyCode.E)) OnStrikeDetected?.Invoke("Right", "PUNCH_STRAIGHT", _rightHand.palmPos, nowMs);
            if (WasKeyPressed(KeyCode.A)) OnStrikeDetected?.Invoke("Left", "OPEN_PALM", _leftHand.palmPos, nowMs);
            if (WasKeyPressed(KeyCode.D)) OnStrikeDetected?.Invoke("Right", "OPEN_PALM", _rightHand.palmPos, nowMs);
        }

        private bool WasSpacePressed()
        {
#if ENABLE_INPUT_SYSTEM
            return Keyboard.current != null && Keyboard.current.spaceKey.wasPressedThisFrame;
#else
            return Input.GetKeyDown(KeyCode.Space);
#endif
        }

        private bool WasKeyPressed(KeyCode key)
        {
#if ENABLE_INPUT_SYSTEM
            if (Keyboard.current == null) return false;
            switch (key)
            {
                case KeyCode.Q: return Keyboard.current.qKey.wasPressedThisFrame;
                case KeyCode.E: return Keyboard.current.eKey.wasPressedThisFrame;
                case KeyCode.A: return Keyboard.current.aKey.wasPressedThisFrame;
                case KeyCode.D: return Keyboard.current.dKey.wasPressedThisFrame;
                default: return false;
            }
#else
            return Input.GetKeyDown(key);
#endif
        }
    }
}