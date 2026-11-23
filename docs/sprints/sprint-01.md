# Sprint 1 (16/11 – 22/11): Nền móng

> Lộ trình và quy ước chung: [README.md](README.md)

| Ai | Việc | Xong khi |
|---|---|---|
| Thái | Đưa khung Python từ `44a3e6b` vào thư mục `python/` của repo Unity. Capture luồng riêng + MediaPipe 2 tay. Gửi vị trí tay (`HAND_POSE`) qua UDP, viết script C# nhận | Unity in ra console toạ độ 2 tay theo thời gian thực |
| Duy | Phân biệt tay trái/phải theo góc nhìn người chơi (chốt lật gương ở một chỗ). Nhận đấm thẳng từ landmark, vẽ kết quả bằng OpenCV | Cửa sổ OpenCV hiện đúng "trái/phải" và nháy khi đấm thẳng |
| Thảo | Học Unity. Dựng cảnh: đường chạy, máy bắn phóng khối bên trái/phải, vùng đánh. Bàn phím giả lập cú đánh | Bấm phím đúng bên khi khối tới vùng đánh thì khối biến mất |
| Cả nhóm | Chốt định dạng tin UDP, `FrameResult`, tên loại cú đánh (`PUNCH_STRAIGHT`, `BLOCK`, `OPEN_PALM`). Chốt tư thế "đấm thủ", vai trò "xoè tay", có làm "hình phản chiếu" hay không | Ghi vào [`PHAN_CONG.vi.md`](../team/PHAN_CONG.vi.md), mục "Cần chốt thêm" không còn câu hỏi |

## Chi tiết (cập nhật T5 19/11)

**T5 19/11:** đã xong bước T4 của Thái: `python/`, `models/gesture_recognizer.task` và 3 script Unity (`Assets/_Project/Network/`, `Assets/_Project/Gameplay/`) đã có trên `main`. Cài đặt theo mục "Lệnh" trong [`AGENTS.md`](../../AGENTS.md) (Python 3.12, venv ở `python/.venv`). Duy và Thảo pull về là chạy được. Chạy thử 20 giây trên máy Thái: `recognize` p50 ≈ 25 ms nhưng chỉ ~10 FPS, cần xem lại webcam trước khi ghi baseline T7.

Đến 18/11 chưa có việc nào xong, còn 5 ngày (T4 → CN). Nhiều thứ đã có sẵn trong commit `44a3e6b`, phần lớn việc tuần này là lấy lại và làm cho chạy:

| Có sẵn trong `44a3e6b` | Trạng thái |
|---|---|
| `python/punchar/capture/camera.py`: capture luồng riêng, chỉ giữ frame mới nhất, lật gương | Đã viết, chưa chạy thử trên repo mới |
| `python/punchar/recognizer/`: interface `FrameResult`, adapter MediaPipe, replay | Đã viết |
| `python/punchar/decision/state_machine.py`: khung state machine, hàm `hand_size()` | Chỉ có khung, phần chuyển trạng thái còn `TODO` |
| `python/punchar/transport/udp_sender.py`: gửi tin `pose` / `strike` / `hand_lost` | Đã viết |
| `python/config/default.toml`: ngưỡng đấm thẳng, cooldown, cổng UDP | Đã viết, số chưa chỉnh |
| `unity/Assets/Scripts/`: `UdpReceiver.cs`, `Messages.cs`, `GameManager.cs` (phím `F`/`J` giả lập đấm) | Đã viết |
| `models/gesture_recognizer.task` (8 MB) | Bị xoá ở commit `0587ebe`, đã lấy lại (T5) |

**Quy ước để không giẫm chân nhau:** code đặt đúng thư mục theo [`code-structure.md`](../team/code-structure.md), làm trên nhánh riêng theo [`gitflow.md`](../team/gitflow.md). Mỗi người một scene riêng `Assets/Scenes/Sandbox_<Tên>.unity`, không sửa scene của người khác. Script dùng chung (`UdpReceiver.cs`, `Messages.cs`) do Thái giữ; ai cần sửa thì báo Thái.

### Thái: Pipeline + cầu nối UDP

| Ngày | Bước | Xong khi |
|---|---|---|
| T4 18/11 | Lấy lại `python/`, `models/gesture_recognizer.task` và 3 script Unity từ `44a3e6b`. Script Unity đặt theo [`code-structure.md`](../team/code-structure.md): `UdpReceiver.cs`, `Messages.cs` vào `Assets/_Project/Network/`, `GameManager.cs` vào `Assets/_Project/Gameplay/` (repo không còn thư mục `unity/`). Tạo venv, cài `python/requirements.txt`. Mở PR và merge vào `main` (theo [`gitflow.md`](../team/gitflow.md)) | Trên máy Thái chạy được `python -m punchar.main` (từ `python/`), Ctrl+C in ra bảng thời gian. **Duy và Thảo pull được ngay trong tối T4** |
| T5 19/11 | Viết bản đề xuất hợp đồng dữ liệu: định dạng 3 tin UDP (lấy từ `udp_sender.py` và `Messages.cs`), hệ toạ độ `x, y` (0–1, gốc ở đâu, đã lật gương), tên `kind`. Thêm vào mục "Chỗ giao nhau" của [`PHAN_CONG.vi.md`](../team/PHAN_CONG.vi.md), gửi nhóm | Duy và Thảo đã đọc, góp ý trước tối T6 |
| T5–T6 | Tạo `Sandbox_Thai.unity`: gắn `UdpReceiver`, viết script đọc tin `pose` và di chuyển 2 quả cầu (trái/phải) theo `x, y` | Giơ 2 tay trước webcam, 2 quả cầu trong Unity chạy theo |
| T7 21/11 | Ghi số baseline từ bảng thời gian của `main.py`: FPS, thời gian `recognize`, `since_capture` khi có 2 tay trong hình | Có 3 con số, ghi vào mục "Review" cuối file |
| CN 22/11 | Demo ở buổi họp; chốt hợp đồng dữ liệu | Hợp đồng ghi trong [`PHAN_CONG.vi.md`](../team/PHAN_CONG.vi.md), đánh dấu "đã chốt" |

### Duy: Tay trái/phải + đấm thẳng

Cần chờ: Thái push `python/` (tối T4). Trong lúc chờ, đọc `state_machine.py` và mục 6 của [`PROJECT_OVERVIEW.vi.md`](../planning/PROJECT_OVERVIEW.vi.md).

| Ngày | Bước | Xong khi |
|---|---|---|
| T5 19/11 | Chạy pipeline trên máy mình. Kiểm tra tay trái/phải: `camera.py` đã lật gương ảnh trước khi đưa vào MediaPipe, nên phải thử xem nhãn `handedness` trả về có đúng theo góc nhìn người chơi không. Nếu sai thì sửa **ở một chỗ duy nhất** (trong adapter MediaPipe) và ghi chú lại | Giơ tay phải thật → nhãn `Right`, cả khi chỉ có 1 tay và khi có 2 tay |
| T5–T7 | Cài phần chuyển trạng thái trong `state_machine.py` cho **đấm thẳng**: `IDLE → WINDUP` khi tay nắm (`Closed_Fist`, score ≥ `min_shape_score`); `WINDUP → STRIKE` khi `hand_size` tăng ≥ `punch_size_growth` trong `punch_window_ms`; phát `StrikeEvent`; `COOLDOWN` trong `cooldown_ms`. Tham số lấy từ `default.toml`, tính theo ms | Có unit test trong `tests/test_decision.py` với chuỗi `FrameResult` tự tạo: một cú đấm → đúng 1 event; đưa tay lên chậm → 0 event |
| T6–T7 | Công cụ xem trực tiếp (sửa `tools/live_test.py` hoặc thêm `tools/punch_debug.py`): cửa sổ OpenCV hiện khung tay, nhãn `L`/`R`, trạng thái state machine, và nháy màu khi có cú đấm | Cửa sổ hiện đúng trái/phải và nháy khi đấm thẳng |
| T7 21/11 | Thử nhanh: mỗi tay 20 cú đấm thẳng + 20 lần đưa tay lên/xuống không đấm. Đếm số cú nhận đúng và số lần kích hoạt nhầm | Có 2 con số cho mỗi tay, ghi vào mục "Review". Đây là số đầu tiên, chưa cần đạt 90% |
| CN 22/11 | Chuẩn bị đề xuất để nhóm chốt: tư thế "đấm thủ" nhận diện thế nào, "xoè tay" làm gì trong game (Duy là người làm phần nhận diện nên đề xuất trước) | Nhóm chốt ở buổi họp, ghi vào [`PHAN_CONG.vi.md`](../team/PHAN_CONG.vi.md) |

### Thảo: Cảnh game + bàn phím giả lập

Không phải chờ ai, làm song song từ T4.

| Ngày | Bước | Xong khi |
|---|---|---|
| T4 18/11 | Cài Unity **6000.6.4f1** (đúng bản của project, xem `ProjectSettings/ProjectVersion.txt`), clone repo, mở project. Tạo `Sandbox_Thao.unity` | Mở project không lỗi, scene riêng đã push |
| T4–T5 | Dựng cảnh tối giản bằng khối có sẵn của Unity (chưa cần làm đẹp): đường chạy ở giữa, máy bắn ở xa, vùng đánh trước camera chia 2 nửa trái/phải | Nhìn vào scene thấy rõ đường chạy, máy bắn và vùng đánh |
| T5–T6 | Máy bắn phóng khối bay về phía camera, ngẫu nhiên bên trái hoặc phải, theo nhịp cố định (ví dụ 1 khối/giây). Khối bay quá vùng đánh thì tự huỷ và tính "trượt" | Khối bay đều, hai bên, không chồng lên nhau |
| T6–T7 | Bàn phím giả lập cú đánh: `F` = tay trái, `J` = tay phải (giống `GameManager.cs` cũ, đã có trong `Assets/_Project/Gameplay/` sau khi Thái push). Bấm đúng bên khi khối đang ở vùng đánh → khối biến mất, sai bên hoặc sai lúc → không có gì | Bấm phím đúng bên khi khối tới vùng đánh thì khối biến mất |
| T7–CN | Viết xử lý trúng/trượt sao cho phím chỉ là **một nguồn** cú đánh: một hàm nhận `(hand, kind)`, phím gọi hàm đó. Sprint 2 chỉ cần nối tin `strike` từ UDP vào cùng hàm này | Đọc code thấy rõ chỗ để nối UDP; Thái xác nhận khớp với định dạng tin `strike` |

### Cả nhóm: Buổi họp CN 22/11

1. Mỗi người demo phần mình theo cột "Xong khi" ở trên.
2. Chốt hợp đồng dữ liệu (bản Thái gửi T5).
3. Chốt "đấm thủ", "xoè tay", có làm "hình phản chiếu" hay không (đề xuất của Duy).
4. Điền mục "Review" bên dưới, chuyển việc chưa xong sang [Sprint 2](sprint-02.md).

**Nếu tuần này không kịp:** giữ bước T4 của Thái (vì Duy cần) và việc chốt hợp đồng dữ liệu. Số baseline của Thái và phép thử 20 cú của Duy có thể lùi sang đầu Sprint 2.

## Review (điền ở buổi họp CN 22/11)

- **Đạt "Xong khi" của từng người?**
- **Số baseline (Thái):** FPS ~10 · `recognize` p50 ≈ 22 ms · `since_capture` p50 ≈ 24 ms

  Đo T7 21/11 bằng `python -m punchar.main`, webcam trực tiếp 1280×720, 2 tay trong hình, laptop i5-12450H (CPU). Đơn vị ms.

  | Lượt | n | `recognize` p50 / p95 / p99 | `since_capture` p50 / p95 / p99 | `send` p50 |
  |---|---|---|---|---|
  | 1 | 682 | 21.4 / 32.1 / 39.3 | 23.4 / 34.1 / 41.4 | 0.2 |
  | 2 | 780 | 22.0 / 33.1 / 40.8 | 23.9 / 35.1 / 42.7 | 0.1 |

  - `recognize` ổn định giữa 2 lượt (lệch ~3%). `since_capture` − `recognize` ≈ 2 ms: frame được xử lý ngay, không xếp hàng.
  - `decision` = 0.0 ms vì `state_machine.py` chưa có logic, số này chưa có ý nghĩa.
  - Chưa ghi thời gian chạy mỗi lượt nên FPS lấy theo giới hạn webcam: ở 1280×720 webcam dùng YUYV (không nén), `v4l2-ctl` báo tối đa **10 FPS**. Pipeline chạy được ~45 FPS (`recognize` ~22 ms), nên nút thắt là webcam, không phải model.
  - Đã sửa: `camera.py` yêu cầu MJPG → webcam ra 30 FPS ở cùng độ phân giải (đo thử 3 giây: 30.3 FPS).

  **Sau khi bật MJPG** (đo CN 22/11, cùng điều kiện và cách đo như trên):

  | Lượt | n | `recognize` p50 / p95 / p99 | `since_capture` p50 / p95 / p99 | `send` p50 |
  |---|---|---|---|---|
  | MJPG | 2223 | 20.4 / 30.7 / 39.6 | 22.1 / 33.1 / 43.4 | 0.1 |

  - `recognize` và `since_capture` gần như không đổi so với trước (p50 lệch ~1–2 ms): MJPG chỉ gỡ nút thắt ở webcam, không làm chậm model, và frame vẫn được xử lý ngay (`since_capture` − `recognize` ≈ 2 ms).
  - FPS **≈ 30** (trước: ~10): lượt này chạy khoảng 70–75 giây (ước lượng, không bấm giờ), 2223 / 70–75 s ≈ 29.6–31.8 FPS. Webcam giới hạn 30 FPS nên lấy ~30. Pipeline đã theo kịp webcam; giới hạn tiếp theo vẫn là webcam (model cho phép ~45 FPS).
- **Thử đấm thẳng (Duy):** trái …/20 đúng, … lần nhầm · phải …/20 đúng, … lần nhầm
- **Việc chuyển sang Sprint 2:**
