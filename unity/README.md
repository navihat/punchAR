# Unity

Tạo project Unity (3D, Built-in hoặc URP) **ngay trong thư mục này** bằng Unity Hub
(chọn location = `punchAR/`, tên project = `unity`), Unity sẽ giữ nguyên `Assets/Scripts/`.

| Script | Vai trò |
|---|---|
| `UdpReceiver.cs` | Nhận JSON từ Python (cổng 5005) trên thread riêng, đẩy vào queue |
| `Messages.cs` | Định nghĩa các message `pose` / `strike` / `hand_lost` (hợp đồng với Python) |
| `GameManager.cs` | Đọc queue trong `Update()`, xử lý strike; phím `F`/`J` giả lập đấm trái/phải |

Gắn `UdpReceiver` và `GameManager` vào một GameObject trong scene, kéo `UdpReceiver` vào ô `receiver`.
