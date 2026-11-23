using System;
using System.Collections.Concurrent;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

namespace PunchAR.Hand3D
{
    /// <summary>
    /// Nguồn cấp dữ liệu Giai đoạn 1: Nhận UDP JSON từ Python (127.0.0.1:5005)
    /// trên luồng nền, không phụ thuộc thư viện ngoài (dùng UnityEngine.JsonUtility).
    /// </summary>
    public class UdpHandProvider : MonoBehaviour, IHandInputProvider
    {
        [Header("Cấu hình UDP (Khớp pose_config.json)")]
        [SerializeField] private int listenPort = 5005;
        [SerializeField] private int handTimeoutMs = 500;
        [SerializeField] private bool logStrikeEvents = true;

        // DTO ánh xạ trực tiếp bằng JsonUtility (tương thích ngược cả khi thiếu "lm")
        [Serializable]
        private class UdpHandDto
        {
            public string hand;
            public float x;
            public float y;
            public string shape;
            public float[] lm; // Tuỳ chọn: mảng phẳng 63 phần tử [x0,y0,z0 ... x20,y20,z20]
        }

        [Serializable]
        private class UdpPacketDto
        {
            public string type;
            public long t;
            public string hand;
            public string kind;
            public float x;
            public float y;
            public UdpHandDto[] hands;
        }

        private HandFrameData _leftHand;
        private HandFrameData _rightHand;
        private long _lastLatencyMs;
        private float _packetsPerSecond;

        public HandFrameData LeftHand => _leftHand;
        public HandFrameData RightHand => _rightHand;
        public long LastLatencyMs => _lastLatencyMs;
        public float PacketsPerSecond => _packetsPerSecond;
        public event Action<string, string, Vector2, long> OnStrikeDetected;

        private UdpClient _udpClient;
        private Thread _receiveThread;
        private volatile bool _isRunning;
        private readonly ConcurrentQueue<string> _packetQueue = new ConcurrentQueue<string>();

        private int _posePacketCounter;
        private float _ppsTimer;

        private void Awake()
        {
            _leftHand = CreateEmptyHand("Left");
            _rightHand = CreateEmptyHand("Right");
        }

        private void OnEnable()
        {
            StartReceiver();
        }

        private void OnDisable()
        {
            StopReceiver();
        }

        private void OnApplicationQuit()
        {
            StopReceiver();
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

        private void StartReceiver()
        {
            if (_isRunning) return;

            try
            {
                _udpClient = new UdpClient(listenPort);
                _udpClient.Client.ReceiveTimeout = 500; // Cho phép thoát luồng sạch mà không cần Thread.Abort
                _isRunning = true;

                _receiveThread = new Thread(ReceiveLoop)
                {
                    IsBackground = true,
                    Name = "PunchAR_UDP_Receiver"
                };
                _receiveThread.Start();

                Debug.Log($"[UdpHandProvider] Đang lắng nghe UDP tại cổng {listenPort}...");
            }
            catch (Exception ex)
            {
                Debug.LogError($"[UdpHandProvider] Không thể mở cổng UDP {listenPort}: {ex.Message}");
            }
        }

        private void StopReceiver()
        {
            _isRunning = false;

            if (_udpClient != null)
            {
                try { _udpClient.Close(); } catch { }
                _udpClient = null;
            }

            if (_receiveThread != null && _receiveThread.IsAlive)
            {
                _receiveThread.Join(300);
                _receiveThread = null;
            }
        }

        private void ReceiveLoop()
        {
            IPEndPoint remoteEp = new IPEndPoint(IPAddress.Any, 0);

            while (_isRunning)
            {
                try
                {
                    byte[] bytes = _udpClient.Receive(ref remoteEp);
                    if (bytes != null && bytes.Length > 0)
                    {
                        string json = Encoding.UTF8.GetString(bytes);
                        _packetQueue.Enqueue(json);
                    }
                }
                catch (SocketException sex)
                {
                    // Timeout định kỳ để kiểm tra cờ _isRunning -> bỏ qua
                    if (sex.SocketErrorCode == SocketError.TimedOut) continue;
                    if (!_isRunning) break;
                }
                catch (ObjectDisposedException)
                {
                    break;
                }
                catch (Exception ex)
                {
                    if (_isRunning)
                        Debug.LogWarning($"[UdpHandProvider] Lỗi nhận UDP: {ex.Message}");
                }
            }
        }

        private void Update()
        {
            long nowMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();

            // Đọc toàn bộ gói tin trong hàng đợi (tránh dồn trễ buffer)
            while (_packetQueue.TryDequeue(out string json))
            {
                ProcessJson(json, nowMs);
            }

            // Tự động ẩn tay nếu quá handTimeoutMs không nhận được gói pose mới (phòng rớt gói UDP)
            if (_leftHand.isTracked && (nowMs - _leftHand.receivedAtMs) > handTimeoutMs)
                _leftHand.isTracked = false;

            if (_rightHand.isTracked && (nowMs - _rightHand.receivedAtMs) > handTimeoutMs)
                _rightHand.isTracked = false;

            // Tính tốc độ nhận gói pose/giây phục vụ Debug HUD
            _ppsTimer += Time.unscaledDeltaTime;
            if (_ppsTimer >= 1.0f)
            {
                _packetsPerSecond = _posePacketCounter / _ppsTimer;
                _posePacketCounter = 0;
                _ppsTimer = 0f;
            }
        }

        private void ProcessJson(string json, long nowMs)
        {
            UdpPacketDto pkt;
            try
            {
                pkt = JsonUtility.FromJson<UdpPacketDto>(json);
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[UdpHandProvider] JSON không hợp lệ: {ex.Message}");
                return;
            }

            if (pkt == null || string.IsNullOrEmpty(pkt.type)) return;

            if (pkt.t > 0)
            {
                long delta = nowMs - pkt.t;
                if (delta >= 0 && delta < 5000) _lastLatencyMs = delta;
            }

            if (pkt.type == "pose")
            {
                _posePacketCounter++;
                bool seenLeft = false;
                bool seenRight = false;

                if (pkt.hands != null)
                {
                    for (int i = 0; i < pkt.hands.Length; i++)
                    {
                        UdpHandDto h = pkt.hands[i];
                        if (h == null) continue;

                        if (h.hand == "Left")
                        {
                            ApplyHandDto(ref _leftHand, h, pkt.t, nowMs);
                            seenLeft = true;
                        }
                        else if (h.hand == "Right")
                        {
                            ApplyHandDto(ref _rightHand, h, pkt.t, nowMs);
                            seenRight = true;
                        }
                    }
                }

                // Nếu trong gói pose không có tay nào đó -> đánh dấu không track
                if (!seenLeft && (nowMs - _leftHand.receivedAtMs) > 120) _leftHand.isTracked = false;
                if (!seenRight && (nowMs - _rightHand.receivedAtMs) > 120) _rightHand.isTracked = false;
            }
            else if (pkt.type == "strike")
            {
                Vector2 pos = new Vector2(pkt.x, pkt.y);
                if (logStrikeEvents)
                {
                    Debug.Log($"[UdpHandProvider] STRIKE | Tay: {pkt.hand} | Loại: {pkt.kind} | Pos: ({pos.x:F2}, {pos.y:F2}) | Latency: {_lastLatencyMs} ms");
                }
                OnStrikeDetected?.Invoke(pkt.hand, pkt.kind, pos, pkt.t);
            }
            else if (pkt.type == "hand_lost")
            {
                if (pkt.hand == "Left") _leftHand.isTracked = false;
                else if (pkt.hand == "Right") _rightHand.isTracked = false;
            }
        }

        private void ApplyHandDto(ref HandFrameData target, UdpHandDto dto, long sourceTsMs, long nowMs)
        {
            target.isTracked = true;
            target.hand = dto.hand;
            target.palmPos = new Vector2(Mathf.Clamp01(dto.x), Mathf.Clamp01(dto.y));
            target.shape = string.IsNullOrEmpty(dto.shape) ? "None" : dto.shape;
            target.sourceTimestampMs = sourceTsMs;
            target.receivedAtMs = nowMs;

            if (target.landmarks == null || target.landmarks.Length != 21)
                target.landmarks = new Vector3[21];

            if (dto.lm != null && dto.lm.Length == 63)
            {
                for (int i = 0; i < 21; i++)
                {
                    int idx = i * 3;
                    // Đảo dấu Y để khớp hệ toạ độ +Y hướng lên của Unity
                    target.landmarks[i] = new Vector3(dto.lm[idx], -dto.lm[idx + 1], dto.lm[idx + 2]);
                }
                target.hasLandmarks = true;
            }
            else
            {
                // Tương thích ngược nếu gói UDP chỉ gửi 4 trường cơ bản (chưa có lm)
                target.hasLandmarks = false;
            }
        }
    }
}