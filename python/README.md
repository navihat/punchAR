# Pipeline Nhận Diện Cử Chỉ Tay Thời Gian Thực (`punchar`)

> **Học phần:** ED4140 — Đồ án VR/AR  
> **Đề tài:** Các kỹ thuật hỗ trợ mô hình AI đáp ứng thời gian thực trong xử lý chuỗi hình ảnh  
> **Phụ trách cử chỉ & bộ dữ liệu:** Duy

Hệ thống xử lý chuỗi hình ảnh từ webcam, nhận diện cử chỉ bàn tay (MediaPipe Gesture Recognizer), lọc rung lắc động học (One-Euro Filter), xác định các cú đánh thông qua State Machine và truyền dữ liệu qua UDP sang Unity (`127.0.0.1:5005`).

---

## 1. Cấu Trúc Thư Mục

```text
python/
├── punchar/                    # Gói mã nguồn chính của pipeline
│   ├── capture/                # Đọc webcam đa luồng (LatestFrameCapture, Camera)
│   ├── recognizer/             # Interface Recognizer và adapter MediaPipe
│   ├── decision/               # Logic quyết định cử chỉ (Duy phụ trách)
│   │   ├── state_machine.py    # Máy trạng thái từng tay (PUNCH, BLOCK, PALM)
│   │   ├── filter.py           # Bộ lọc One-Euro khử rung giật landmark
│   │   └── features.py         # Trích xuất đặc trưng hình dạng và động học
│   ├── transport/              # Đóng gói JSON và gửi UDP sang Unity
│   ├── metrics/                # Đo độ trễ từng khâu (timing, report)
│   └── main.py                 # Vòng lặp pipeline chính
├── config/
│   └── default.toml            # Toàn bộ tham số và ngưỡng (thời gian tính bằng ms)
├── data/                       # Dữ liệu mẫu và cấu hình cử chỉ
│   ├── pose_templates.npz      # Vector đặc trưng trung bình của từng thế tay
│   ├── pose_config.json        # Ngưỡng động học chi tiết của các thế
│   ├── gesture_dataset.npz     # Toàn bộ dữ liệu toạ độ landmark đã thu thập
│   └── dataset_images/         # Ảnh chụp mẫu (full frame và crop bàn tay)
├── tools/                      # Công cụ thu thập, kiểm thử và giả lập
│   ├── collect_and_label.py    # Thu thập mẫu và gán nhãn tự động
│   ├── punch_debug.py          # Kiểm thử nhận diện trực quan trên OpenCV + UDP
│   ├── mock_hand_sender.py     # Giả lập cử chỉ phát UDP sang Unity
│   ├── benchmark.py            # Đo hiệu năng trên video quay sẵn
│   └── eval_dataset.py         # Đánh giá độ chính xác trên tập ảnh
├── tests/                      # Kiểm thử tự động (pytest)
│   └── test_decision.py        # Unit test cho logic máy trạng thái
└── requirements.txt            # Danh sách thư viện phụ thuộc
```

---

## 2. Cài Đặt Môi Trường

Dự án yêu cầu **Python 3.12**. Khuyến nghị sử dụng `uv` để tự động tải đúng bản Python và cài đặt thư viện:

```powershell
# Chạy từ thư mục python/
cd python

# Tạo môi trường ảo với Python 3.12
uv venv --python 3.12 .venv

# Kích hoạt môi trường ảo (Windows PowerShell)
.\.venv\Scripts\activate

# Cài đặt các thư viện cần thiết
uv pip install -r requirements.txt
```

---

## 3. Hướng Dẫn Sử Dụng Các Công Cụ

### Công Cụ 1: Thu Thập Mẫu & Gán Nhãn Cử Chỉ Tự Động
Dùng để ghi lại dữ liệu cử chỉ của người chơi, xuất file template vector trung bình `.npz` và cấu hình ngưỡng `.json`.

```powershell
python tools/collect_and_label.py
```

**Các phím tắt điều khiển:**
- `1`: Chọn thế **Đấm thẳng** (`PUNCH_STRAIGHT`)
- `2`: Chọn thế **Xoè tay** (`OPEN_PALM`)
- `3`: Chọn thế **Đấm thủ / Đỡ** (`BLOCK`)
- `0`: Chọn thế **Thả lỏng** (`IDLE`)
- `SPACE`: **Bắt đầu đếm ngược 3 giây**, sau đó chương trình tự động thu thập liên tục cho đến khi đủ **50 mẫu hợp lệ** (nhấn `SPACE` lần nữa nếu muốn tạm dừng).
- `c`: Chụp nhanh khung hình hiện tại lưu vào `data/dataset_images/snapshots/`.
- `r`: Xóa mẫu thu tạm thời của thế đang chọn nếu làm sai động tác.
- `s`: **Lưu toàn bộ dữ liệu**. File sinh ra đặt tại `python/data/`:
  - `pose_templates.npz`: Vector trung bình hình dạng từng thế.
  - `pose_config.json`: Ngưỡng động học và vận tốc chuẩn.
  - `gesture_dataset.npz`: Toàn bộ mảng toạ độ landmark.
  - `dataset_images/`: Lưu ảnh full frame và crop từng bàn tay.
- `q`: Thoát công cụ.

---

### Công Cụ 2: Kiểm Thử Trực Quan & Truyền UDP Sang Unity (`punch_debug.py`)
Mở cửa sổ OpenCV hiển thị khung xương tay, nhãn phân biệt Trái/Phải, trạng thái máy trạng thái (IDLE, WINDUP, STRIKE, COOLDOWN), và gửi gói tin UDP trực tiếp tới Unity (`127.0.0.1:5005`).

```powershell
python tools/punch_debug.py
```

**Đặc điểm:**
- Hiển thị HUD trực tiếp: tốc độ xử lý (FPS), độ trễ (ms), độ tin cậy của MediaPipe, và nháy viền màu xanh lá khi phát hiện cú đấm hợp lệ.
- Tự động kết nối UDP socket `127.0.0.1:5005`.
- Nhấn `q` để dừng chương trình.

---

### Công Cụ 3: Giả Lập Cử Chỉ Tay Không Cần Webcam (`mock_hand_sender.py`)
Phục vụ việc kiểm thử bên Unity khi không có webcam hoặc máy không tiện mở camera:

```powershell
python tools/mock_hand_sender.py
```
- Tự động sinh toạ độ hai bàn tay di chuyển theo quỹ đạo mượt mà, gập ngón tay và định kỳ phát các cú đấm giả lập sang cổng UDP `5005`.

---

### Chạy Toàn Bộ Pipeline Chính (`main.py`)
Khi tích hợp hoàn chỉnh với hệ thống đo đạc thời gian và cầu nối Unity:

```powershell
python -m punchar.main
```
- Nhấn `Ctrl+C` để dừng chương trình. Hệ thống sẽ in ra bảng tổng kết thời gian (p50, p95, p99) ở từng khâu: `recognize`, `decision`, `send`, `since_capture`.

---

## 4. Nguyên Lý Nhận Diện & Bộ Cử Chỉ

MediaPipe chỉ nhận diện hình dạng bàn tay **tĩnh** (`Closed_Fist`, `Open_Palm`). Để biến thành cú đánh trong game, hệ thống kết hợp hình dạng tay với **chuyển động của landmark theo chuỗi thời gian**:

```
Webcam → LatestFrameCapture → MediaPipe Hands (21 Landmark)
                 ↓
       OneEuroFilter (Khử rung lắc)
                 ↓
  Trích xuất đặc trưng (hand_size, r_open, vận tốc v_scale)
                 ↓
   State Machine từng tay (IDLE → WINDUP → STRIKE → COOLDOWN)
                 ↓
       UDP Broadcast (127.0.0.1:5005)
```

### Bộ 3 Cử Chỉ Cốt Lõi:
1. **Đấm thẳng (`PUNCH_STRAIGHT`):**
   - Hình dạng: Tay nắm chặt (`Closed_Fist`, độ co ngón $r_{open} \le 1.28$).
   - Động học: Kích thước bàn tay $hand\_size$ (khoảng cách Landmark 0 đến 9) tăng nhanh trong cửa sổ $punch\_window\_ms$ (vận tốc lao về phía camera $v_{scale} \ge 1.30$).
2. **Đấm thủ / Đỡ đòn (`BLOCK`):**
   - Hình dạng: Tay nắm chặt trước mặt/ngực ($0.18 \le y \le 0.82$).
   - Động học: Giữ vị trí ổn định liên tục trong thời gian $\ge block\_hold\_ms$ ($120\text{ ms}$), vận tốc di chuyển nhỏ hơn ngưỡng trôi ($v_{planar} \le 0.85$).
3. **Xoè tay / Đẩy chưởng (`OPEN_PALM`):**
   - Hình dạng: Lòng bàn tay mở rộng ($r_{open} \ge 1.48$ hoặc shape `Open_Palm`).
   - Động học: Đẩy bàn tay về phía trước camera ($scale\_gain \ge 0.12$).

---

## 5. Hợp Đồng Bản Tin UDP (`127.0.0.1:5005`)

Dữ liệu trao đổi qua JSON không nén:

### 1. Bản tin `pose` (Gửi liên tục mỗi frame)
```json
{
  "type": "pose",
  "t": 1795072926644,
  "hands": [
    {
      "hand": "Right",
      "x": 0.7312,
      "y": 0.5979,
      "shape": "Closed_Fist",
      "lm": [0.7101, 0.4520, 0.0, 0.7350, 0.4811, -0.0123, "... 63 floats ..."]
    }
  ]
}
```
- `t`: Dấu thời gian chụp frame gốc (Unix epoch ms).
- `lm`: Mảng phẳng gồm 63 số thực (21 điểm landmark 3D $x, y, z$) dùng để Unity uốn gập 15 đốt xương tay.

### 2. Bản tin `strike` (Gửi một lần khi xác nhận cú đánh)
```json
{
  "type": "strike",
  "t": 1795072926711,
  "hand": "Left",
  "kind": "PUNCH_STRAIGHT",
  "x": 0.3120,
  "y": 0.5521
}
```
- `kind`: Một trong ba giá trị `PUNCH_STRAIGHT`, `BLOCK`, `OPEN_PALM`.

### 3. Bản tin `hand_lost` (Khi mất dấu tay quá `lost_grace_ms`)
```json
{
  "type": "hand_lost",
  "t": 1795072927010,
  "hand": "Right"
}
```

---

## 6. Chạy Kiểm Thử Tự Động (Unit Test)

Chạy bộ test kiểm tra logic chuyển trạng thái và tính đúng đắn của máy trạng thái:

```powershell
python -m pytest tests/ -v
```
