using System;
using UnityEngine;

namespace PunchAR.Hand3D
{
    /// <summary>
    /// Nguồn cấp dữ liệu Giai đoạn 1: Nhận UDP từ UdpReceiver (_Project/Network)
    /// Đóng vai trò Subscriber trong mô hình Observer, loại bỏ xung đột socket cổng 5005.
    /// </summary>
    public class UdpHandProvider : MonoBehaviour, IHandInputProvider
    {
        [Header("Nguồn nhận UDP")]
        [SerializeField] private UdpReceiver udpReceiver;
        [SerializeField] private int handTimeoutMs = 500;
        [SerializeField] private bool logStrikeEvents = true;

        private HandFrameData _leftHand;
        private HandFrameData _rightHand;
        private long _lastLatencyMs;
        private float _packetsPerSecond;

        public HandFrameData LeftHand => _leftHand;
        public HandFrameData RightHand => _rightHand;
        public long LastLatencyMs => _lastLatencyMs;
        public float PacketsPerSecond => _packetsPerSecond;
        public event Action<string, string, Vector2, long> OnStrikeDetected;

        private int _posePacketCounter;
        private float _ppsTimer;

        private void Awake()
        {
            _leftHand = CreateEmptyHand("Left");
            _rightHand = CreateEmptyHand("Right");

            if (udpReceiver == null)
            {
                udpReceiver = FindFirstObjectByType<UdpReceiver>();
            }
        }

        private void OnEnable()
        {
            if (udpReceiver == null)
            {
                udpReceiver = FindFirstObjectByType<UdpReceiver>();
            }
            if (udpReceiver != null)
            {
                udpReceiver.OnPoseReceived += HandlePose;
                udpReceiver.OnStrikeReceived += HandleStrike;
                udpReceiver.OnHandLostReceived += HandleHandLost;
            }
        }

        private void OnDisable()
        {
            if (udpReceiver != null)
            {
                udpReceiver.OnPoseReceived -= HandlePose;
                udpReceiver.OnStrikeReceived -= HandleStrike;
                udpReceiver.OnHandLostReceived -= HandleHandLost;
            }
        }

        private void Update()
        {
            long nowMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();

            if (_leftHand.isTracked && (nowMs - _leftHand.receivedAtMs) > handTimeoutMs)
                _leftHand.isTracked = false;

            if (_rightHand.isTracked && (nowMs - _rightHand.receivedAtMs) > handTimeoutMs)
                _rightHand.isTracked = false;

            _ppsTimer += Time.unscaledDeltaTime;
            if (_ppsTimer >= 1.0f)
            {
                _packetsPerSecond = _posePacketCounter / _ppsTimer;
                _posePacketCounter = 0;
                _ppsTimer = 0f;
            }
        }

        private void HandlePose(PoseMessage pkt)
        {
            if (pkt == null) return;
            long nowMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();

            if (pkt.t > 0)
            {
                long delta = nowMs - pkt.t;
                if (delta >= 0 && delta < 5000) _lastLatencyMs = delta;
            }

            _posePacketCounter++;
            bool seenLeft = false;
            bool seenRight = false;

            if (pkt.hands != null)
            {
                for (int i = 0; i < pkt.hands.Length; i++)
                {
                    HandPose h = pkt.hands[i];
                    if (h == null) continue;

                    if (h.hand == "Left")
                    {
                        ApplyHandPose(ref _leftHand, h, pkt.t, nowMs);
                        seenLeft = true;
                    }
                    else if (h.hand == "Right")
                    {
                        ApplyHandPose(ref _rightHand, h, pkt.t, nowMs);
                        seenRight = true;
                    }
                }
            }

            if (!seenLeft && (nowMs - _leftHand.receivedAtMs) > 120) _leftHand.isTracked = false;
            if (!seenRight && (nowMs - _rightHand.receivedAtMs) > 120) _rightHand.isTracked = false;
        }

        private void HandleStrike(StrikeMessage pkt)
        {
            if (pkt == null) return;
            Vector2 pos = new Vector2(pkt.x, pkt.y);
            if (logStrikeEvents)
            {
                Debug.Log($"[UdpHandProvider] STRIKE | Tay: {pkt.hand} | Loại: {pkt.kind} | Pos: ({pos.x:F2}, {pos.y:F2}) | Latency: {_lastLatencyMs} ms");
            }
            OnStrikeDetected?.Invoke(pkt.hand, pkt.kind, pos, pkt.t);
        }

        private void HandleHandLost(HandLostMessage pkt)
        {
            if (pkt == null) return;
            if (pkt.hand == "Left") _leftHand.isTracked = false;
            else if (pkt.hand == "Right") _rightHand.isTracked = false;
        }

        private void ApplyHandPose(ref HandFrameData target, HandPose pose, long sourceTsMs, long nowMs)
        {
            target.isTracked = true;
            target.hand = pose.hand;
            target.palmPos = new Vector2(Mathf.Clamp01(pose.x), Mathf.Clamp01(pose.y));
            target.shape = string.IsNullOrEmpty(pose.shape) ? "None" : pose.shape;
            target.sourceTimestampMs = sourceTsMs;
            target.receivedAtMs = nowMs;

            if (target.landmarks == null || target.landmarks.Length != 21)
                target.landmarks = new Vector3[21];

            if (pose.lm != null && pose.lm.Length == 63)
            {
                for (int i = 0; i < 21; i++)
                {
                    int idx = i * 3;
                    // Toạ độ từ Messages.cs: x, y, z (x, y đã lật chuẩn theo Viewport)
                    target.landmarks[i] = new Vector3(pose.lm[idx], -pose.lm[idx + 1], pose.lm[idx + 2]);
                }
                target.hasLandmarks = true;
            }
            else
            {
                target.hasLandmarks = false;
            }
        }

        private HandFrameData CreateEmptyHand(string side)
        {
            return new HandFrameData
            {
                isTracked = false,
                hand = side,
                palmPos = new Vector2(side == "Left" ? 0.3f : 0.7f, 0.5f),
                shape = "None",
                hasLandmarks = false,
                landmarks = new Vector3[21],
                sourceTimestampMs = 0,
                receivedAtMs = 0
            };
        }
    }
}
