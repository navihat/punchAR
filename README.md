# Test MediaPipe Gesture Recognizer

Dùng model mã nguồn mở [MediaPipe Gesture Recognizer](https://ai.google.dev/edge/mediapipe/solutions/vision/gesture_recognizer)
(`models/gesture_recognizer.task`) để đánh giá độ ổn định và độ chính xác nhận diện cử chỉ tay.

Các cử chỉ có sẵn: `None, Closed_Fist, Open_Palm, Pointing_Up, Thumb_Down, Thumb_Up, Victory, ILoveYou`.

## Cấu trúc thư mục

```
punchAR/
├── punchar/              # mã nguồn
│   ├── recognizer.py     # tải model MediaPipe, vẽ kết quả
│   ├── report.py         # accuracy, precision/recall/F1, confusion matrix
│   ├── live_test.py      # test realtime bằng webcam
│   └── eval_dataset.py   # đánh giá offline trên thư mục ảnh
├── models/               # gesture_recognizer.task
├── docs/                 # tổng quan dự án, phân công
├── results/              # báo cáo sinh ra (không commit)
└── requirements.txt
```

Chạy các lệnh từ thư mục gốc của repo.

## Cài đặt

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
# model (đã tải sẵn trong models/)
curl -L -o models/gesture_recognizer.task \
  https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/latest/gesture_recognizer.task
```

## 1. Test realtime bằng webcam — `punchar/live_test.py`

```bash
.venv/bin/python -m punchar.live_test                  # webcam 0
.venv/bin/python -m punchar.live_test --num-hands 2 --det-conf 0.6
```

Màn hình hiển thị:
- **FPS / latency**: tốc độ xử lý mỗi frame.
- **Detect rate**: tỉ lệ frame phát hiện được tay.
- **Flicker**: tỉ lệ frame mà nhãn bị đổi so với frame trước (90 frame gần nhất) → càng thấp càng **ổn định**.
- **Mean conf**: độ tự tin trung bình.
- **Acc**: độ chính xác so với nhãn thật bạn chọn.

Phím tắt:

| Phím | Chức năng |
|---|---|
| `0`–`7` | Chọn cử chỉ thật (ground truth) bạn đang làm |
| `SPACE` | Bắt đầu / dừng ghi mẫu có nhãn |
| `r` | Reset thống kê |
| `s` | Lưu báo cáo vào `results/` |
| `q` / `ESC` | Thoát (tự lưu báo cáo nếu có mẫu) |

Quy trình test độ chính xác: bấm số của cử chỉ → giữ cử chỉ → `SPACE` ghi vài giây → `SPACE` dừng → đổi cử chỉ khác, lặp lại → `s` để xuất báo cáo (accuracy, precision/recall/F1 từng lớp, confusion matrix + CSV từng frame).

Gợi ý kịch bản test độ ổn định: thay đổi ánh sáng, khoảng cách (0.5 m – 2 m), góc nghiêng tay, nền phức tạp, tay trái/phải, di chuyển nhanh.

## 2. Đánh giá offline trên bộ ảnh — `punchar/eval_dataset.py`

```
dataset/
  Thumb_Up/   *.jpg
  Open_Palm/  *.jpg
  None/       *.jpg
```

```bash
.venv/bin/python -m punchar.eval_dataset dataset/
```

Tên thư mục phải trùng tên cử chỉ ở trên. Kết quả lưu trong `results/`.
