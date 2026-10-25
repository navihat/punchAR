# Test MediaPipe Gesture Recognizer

Dùng model mã nguồn mở [MediaPipe Gesture Recognizer](https://ai.google.dev/edge/mediapipe/solutions/vision/gesture_recognizer)
(`models/gesture_recognizer.task`) để đánh giá độ ổn định và độ chính xác nhận diện cử chỉ tay.

Các cử chỉ có sẵn: `None, Closed_Fist, Open_Palm, Pointing_Up, Thumb_Down, Thumb_Up, Victory, ILoveYou`.

## Cấu trúc thư mục

```
punchAR/
├── python/                         # toàn bộ phía Python (chạy lệnh từ thư mục này)
│   ├── punchar/
│   │   ├── capture/camera.py       # [1] thread đọc webcam, chỉ giữ frame mới nhất
│   │   ├── recognizer/             # [2] interface + adapter
│   │   │   ├── base.py             #     FrameResult, HandResult, Recognizer
│   │   │   ├── mediapipe_recognizer.py
│   │   │   └── replay_recognizer.py
│   │   ├── decision/state_machine.py  # [3] IDLE→WINDUP→STRIKE→COOLDOWN (TODO)
│   │   ├── transport/udp_sender.py # gửi JSON pose/strike/hand_lost sang Unity
│   │   ├── metrics/                # timing.py (p50/p95/p99), report.py (accuracy)
│   │   ├── config.py, paths.py
│   │   └── main.py                 # pipeline đầy đủ
│   ├── tools/                      # live_test.py, eval_dataset.py, benchmark.py
│   ├── tests/                      # pytest cho decision logic
│   ├── config/default.toml         # mọi ngưỡng, thời gian (ms), cổng
│   └── requirements.txt
├── unity/                          # [4] game Unity (xem unity/README.md)
├── models/                         # gesture_recognizer.task
├── data/                           # videos/, dataset/ (không commit)
├── results/                        # báo cáo sinh ra (không commit)
└── docs/                           # tổng quan dự án, phân công
```

## Cài đặt

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r python/requirements.txt
# model (đã tải sẵn trong models/)
curl -L -o models/gesture_recognizer.task \
  https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/latest/gesture_recognizer.task
```

Các lệnh bên dưới chạy **từ thư mục `python/`** (`cd python`).

## 0. Pipeline đầy đủ — `punchar/main.py`

```bash
../.venv/bin/python -m punchar.main          # webcam → nhận diện → UDP 127.0.0.1:5005
../.venv/bin/python -m tools.benchmark ../data/videos/clip.mp4
../.venv/bin/python -m pytest tests/
```

Cấu hình trong `config/default.toml`.

## 1. Test realtime bằng webcam — `tools/live_test.py`

```bash
../.venv/bin/python -m tools.live_test                  # webcam 0
../.venv/bin/python -m tools.live_test --num-hands 2 --det-conf 0.6
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

## 2. Đánh giá offline trên bộ ảnh — `tools/eval_dataset.py`

```
data/dataset/
  Thumb_Up/   *.jpg
  Open_Palm/  *.jpg
  None/       *.jpg
```

```bash
../.venv/bin/python -m tools.eval_dataset ../data/dataset/
```

Tên thư mục phải trùng tên cử chỉ ở trên. Kết quả lưu trong `results/`.
