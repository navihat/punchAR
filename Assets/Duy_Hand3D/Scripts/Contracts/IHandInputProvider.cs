using System;
using UnityEngine;

namespace PunchAR.Hand3D
{
    /// <summary>
    /// Cấu trúc dữ liệu khung hình chuẩn cho một bàn tay.
    /// Dùng chung cho Giai đoạn 1 (Python UDP) và Giai đoạn 2 (Unity Native).
    /// </summary>
    public struct HandFrameData
    {
        public bool isTracked;
        public string hand;           // "Left" hoặc "Right"
        public Vector2 palmPos;       // Toạ độ tâm bàn tay P9 chuẩn hoá [0..1] đã lật gương
        public string shape;          // "Closed_Fist" | "Open_Palm" | "None"
        public bool hasLandmarks;     // True nếu gói tin có đủ 21 điểm landmarks
        public Vector3[] landmarks;   // 21 điểm landmarks đã đảo trục +Y hướng lên
        public long sourceTimestampMs;// Dấu thời gian chụp frame gốc từ Python (ms)
        public long receivedAtMs;     // Thời điểm Unity nhận gói tin (ms)
    }

    /// <summary>
    /// Giao diện tách lớp nguồn cấp dữ liệu tay.
    /// Mọi script hiển thị tay 3D và gameplay chỉ đọc từ interface này.
    /// </summary>
    public interface IHandInputProvider
    {
        HandFrameData LeftHand { get; }
        HandFrameData RightHand { get; }

        /// <summary>Độ trễ toàn trình ước lượng (ms) tính từ dấu thời gian t của gói gần nhất.</summary>
        long LastLatencyMs { get; }

        /// <summary>Tần suất gói tin pose nhận được mỗi giây (packets/sec).</summary>
        float PacketsPerSecond { get; }

        /// <summary>
        /// Sự kiện khi xác nhận cú đánh hợp lệ.
        /// Tham số: (hand, kind, normalizedPos, sourceTimestampMs)
        /// </summary>
        event Action<string, string, Vector2, long> OnStrikeDetected;
    }
}