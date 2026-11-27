# TỔNG QUAN DỰ ÁN — Game đấm khối AR kiểu "Move Fast" điều khiển bằng cử chỉ tay (Inference thời gian thực)

> **Cập nhật 27/11/2026** (đang chạy Sprint 2). Bản cho agent code: [`PROJECT_OVERVIEW.md`](PROJECT_OVERVIEW.md), đồng bộ cùng ngày.
> Khi tài liệu này mâu thuẫn với [`DECISIONS.md`](../decisions/DECISIONS.md) thì theo `DECISIONS.md`.
> Mục đánh dấu **[Chưa chốt]** là việc nhóm còn phải quyết. **Câu hỏi thảo luận** chỉ còn giữ những câu chưa có đáp án.

---

## ★ Tóm tắt hiện trạng

| Mục | Đã chốt | Ở đâu |
|---|---|---|
| Game | Game phản xạ đấm khối kiểu Move Fast: hình bay bên nào thì dùng tay bên đó, làm đúng cử chỉ | 26/10, [biên bản](../decisions/2026-10-26_hop-nhom_doi-game-move-fast.md) |
| Cử chỉ | Đấm thẳng, đấm thủ, xoè tay. Đấm móc là tuỳ chọn, đứng đầu danh sách cắt khi trễ | 26/10; [sprints/README.md](../sprints/README.md) |
| Tech stack | Python (nhận diện) + Unity 6000.6.4f1, URP (game, AR), trao đổi JSON qua UDP `127.0.0.1:5005` | 16/11, `DECISIONS.md` |
| VR/AR | AR trên PC: hình webcam làm nền, đối tượng 3D vẽ chồng lên. Không dùng kính VR | Kế hoạch sprint (Sprint 3) |
| Trọng tâm chấm điểm | Kỹ thuật thời gian thực: độ trễ, FPS, độ chính xác và độ ổn định nhận diện. Game là nơi kiểm chứng | [`AGENTS.md`](../../AGENTS.md) |
| Model close source | **Tạm bỏ** (kéo theo ONNX / quantization). Nếu có lại thì xếp sau M3 (27/12) | 16/11, `DECISIONS.md` |
| Hợp đồng tin UDP | 3 tin `pose`, `strike`, `hand_lost`, hệ toạ độ, lật gương | 19/11, [`PHAN_CONG.vi.md`](../team/PHAN_CONG.vi.md) mục "Hợp đồng dữ liệu" |
| Phân công | Thái: pipeline + AR · Duy: cử chỉ tay · Thảo: gameplay | 26/10, [`PHAN_CONG.vi.md`](../team/PHAN_CONG.vi.md) |
| Lộ trình | 8 sprint 1 tuần (16/11/2026 – 10/1/2027), mốc M1–M4 | 16/11, [`sprints/README.md`](../sprints/README.md) |

**Còn mở:**
- Ý nghĩa của "đấm thủ" và "xoè tay" **trong game** (hình nào cần cử chỉ nào, trúng thì xảy ra gì). Cách **nhận diện** thì đã cài theo đề xuất của Duy (mục 6) nhưng chưa ghi vào `DECISIONS.md`. **[Chưa chốt]**
- "Hình phản chiếu" là gì, có làm không. **[Chưa chốt]**
- Tiêu chí thành công: độ chính xác đo theo frame hay theo cú đánh, đo trong điều kiện nào (mục 2). **[Chưa chốt]**
- Cách đưa hình webcam sang Unity khi Python đang giữ camera (việc của Thái trong Sprint 2). **[Chưa chốt]**

---

## 1. Bối cảnh

| Mục | Nội dung |
|---|---|
| Học phần | ED4140 — Đồ án VR/AR (ĐHBK Hà Nội) |
| Đề tài | Các kỹ thuật hỗ trợ mô hình AI đáp ứng thời gian thực trong xử lý chuỗi hình ảnh |
| Sản phẩm | Game phản xạ đấm khối kiểu Move Fast, điều khiển bằng cử chỉ tay, có AR overlay |
| Nền tảng demo | PC + webcam |
| Hạn | Demo giữa tháng 1/2027 (M4: 10/1) |
| Kiểm chứng | Unit test + technical test (latency, FPS, độ chính xác, độ ổn định). Không làm thực nghiệm người dùng |
| Ngoài phạm vi | Ứng dụng phục hồi chức năng / y tế; model close source (tạm bỏ, xem trên) |

### Model nhận diện
- Dùng **MediaPipe Gesture Recognizer** (open source, chạy CPU), file `models/gesture_recognizer.task`.
- Recognizer đi qua interface chung trong `python/punchar/recognizer/base.py`, nên vẫn **thay được model mà không sửa game**.
- Có sẵn 7 hình dạng tay tĩnh: `Closed_Fist, Open_Palm, Pointing_Up, Thumb_Down, Thumb_Up, Victory, ILoveYou` (thêm `None`), 21 landmark mỗi tay (toạ độ ảnh + toạ độ 3D theo mét), phân biệt tay trái/phải.
- **Không có cử chỉ động** (cú đấm). Cú đánh được tính từ chuỗi landmark ở Decision Logic (mục 6).

### Số đo
**Thử ban đầu (10/2026)**, chỉ tính thời gian model, i5-12450H, CPU:

| Cấu hình | Latency trung bình | p95 |
|---|---|---|
| Video mode, theo dõi 1 tay | ~9 ms | 12 ms |
| Video mode, cho phép 2 tay nhưng trong hình chỉ có 1 tay | ~28 ms | 42 ms |
| Image mode (không tracking giữa các frame) | ~21 ms | — |

**Baseline pipeline (22/11, cuối Sprint 1)**, `python -m punchar.main`, webcam trực tiếp 1280×720 MJPG, 2 tay trong hình. Chi tiết và lượt đo trước khi bật MJPG ở [sprint-01.md](../sprints/sprint-01.md), mục "Review".

| `recognize` p50 / p95 / p99 | `since_capture` p50 / p95 / p99 | FPS |
|---|---|---|
| 20.4 / 30.7 / 39.6 ms | 22.1 / 33.1 / 43.4 ms | ≈ 30 (giới hạn của webcam; model cho phép ~45) |

- Trước khi bật MJPG, webcam chỉ ra 10 FPS ở 720p. Nút thắt là webcam, không phải model.
- Chưa có: số đo trên video quay sẵn bằng `benchmark.py`, độ trễ end-to-end đo bằng camera ngoài, độ chính xác nhận diện cú đánh.

---

## 2. Mục tiêu

1. Nhận diện cử chỉ tay từ webcam theo thời gian thực.
2. Chuyển dự đoán từng frame thành hành động game ổn định (logic quyết định theo thời gian).
3. Game đấm khối chơi được (ít nhất Level 1), có AR overlay (đối tượng game vẽ lên hình camera trực tiếp).
4. Tối ưu và **đo lường** toàn pipeline để hệ thống phản hồi tốt khi tài nguyên CPU hạn chế.

### Tiêu chí thành công
Kế hoạch sprint đang dùng các con số sau làm "Xong khi", nhưng nhóm chưa chốt cách đo:
- Độ chính xác trên bộ dữ liệu cú đánh của nhóm: ≥ 90% (Sprint 5)
- Latency end-to-end (tay cử động → game phản hồi): < 100 ms (Sprint 6)
- Tốc độ pipeline: ≥ 25 FPS trên máy chuẩn, kể cả khi giả lập máy yếu (Sprint 5). Hiện đạt ~30 FPS
- Game không giật khi inference đang chạy

**Câu hỏi thảo luận**
- Độ chính xác ≥ 90% đo theo **từng frame** hay theo **từng cú đánh** (sau logic quyết định)? Hai cách cho ra số rất khác nhau.
- Đo trong điều kiện nào: bao nhiêu người, ánh sáng nào, khoảng cách bao xa?
- Có thêm tiêu chí **độ ổn định** không? Ví dụ số lần kích hoạt nhầm mỗi phút.
- "Game không giật" định lượng thế nào? Ví dụ FPS render ≥ 30 và p99 thời gian mỗi frame < 50 ms.

**Đề xuất**
- Chia 2 mức: **mức tối thiểu** (bắt buộc đạt khi demo) và **mức mục tiêu**.
- Đo accuracy ở cả 2 tầng: tầng frame (đánh giá model) và tầng cú đánh (đánh giá trải nghiệm chơi).

---

## 3. Phần cứng

- **Máy đo chuẩn:** Acer Aspire 7 A715-76G — i5-12450H — GTX 1650 4GB VRAM — RAM 8GB. Mọi số benchmark trong báo cáo đo trên máy này.
- Inference chạy trên **CPU**. GPU chỉ dùng để thử nghiệm.
- RAM 8 GB khá chật khi chạy Unity Editor + Python + trình duyệt cùng lúc.
- Một số laptop có camera hồng ngoại ở index 0: chạy với `--camera 1` (xem `config/default.toml`).

**Câu hỏi thảo luận**
- Demo cuối kỳ chạy trên máy nào, webcam nào? (Sprint 8)

---

## 4. Tech stack — ĐÃ CHỐT (16/11/2026)

| Phần | Lựa chọn |
|---|---|
| Capture, nhận diện, logic quyết định, đo | **Python 3.12**: OpenCV, MediaPipe (CPU), numpy, pytest. Quản lý môi trường bằng `uv` |
| Game, render, AR | **Unity 6000.6.4f1**, URP, C#, Input System |
| Cầu nối | **UDP** `127.0.0.1:5005`, mỗi gói một object JSON, một chiều Python → Unity |
| Tham số | `python/config/default.toml`, thời gian tính bằng ms |

Hai phương án bị loại: Python + Pygame (đồ hoạ không đủ cho game 3D) và Web + Three.js (khó đo và tối ưu inference sâu). UDP cộng thêm một khâu vào độ trễ, nhưng khâu này đo được: tin `pose` gửi mất ~0.1 ms (p50).

---

## 5. Kiến trúc hệ thống

```
Webcam → [1] Capture → [2] Recognizer → [3] Decision Logic → (UDP) → [4] Unity: game + AR
          luồng riêng     thay được        ngưỡng, thời gian
                     [5] Metrics: timestamp ở mọi khâu để đo độ trễ
```

| # | Module | Nhiệm vụ | Code |
|---|---|---|---|
| 1 | Capture | Đọc webcam ở luồng riêng, chỉ giữ frame mới nhất, MJPG, lật gương | `python/punchar/capture/camera.py` |
| 2 | Recognizer | Nhận diện tay/cử chỉ qua interface chung. Mỗi model một adapter (`mediapipe`, `replay`) | `python/punchar/recognizer/` |
| 3 | Decision Logic | Làm mượt, ngưỡng, cooldown, state machine từng tay → sinh `strike`, `hand_lost` | `python/punchar/decision/` |
| 4 | Game + AR | Chỉ nhận tin qua UDP, không gọi model trực tiếp | `Assets/_Project/` |
| 5 | Metrics | Ghi timestamp mọi khâu; Ctrl+C in bảng thời gian | `python/punchar/metrics/`, `python/tools/benchmark.py` |

Thư mục nào của ai: [`code-structure.md`](../team/code-structure.md).

### Interface của Recognizer (`recognizer/base.py`)

```python
FrameResult:
    frame_id: int
    timestamp_ms: int          # thời điểm chụp frame, ms theo Unix epoch
    hands: list[HandResult]    # 0, 1 hoặc 2 tay

HandResult:
    handedness: "Left" | "Right"      # tay thật của người chơi
    shape: str                        # "Closed_Fist", "Open_Palm", "None", ...
    score: float                      # 0–1
    landmarks: list[(x, y, z)]        # 21 điểm, toạ độ chuẩn hoá 0–1 theo ảnh
    world_landmarks: list[(x, y, z)]  # 21 điểm, toạ độ 3D theo mét

Recognizer: load(), predict(image, frame_id, timestamp_ms) -> FrameResult, close()
```

### Tin gửi sang Unity — ĐÃ CHỐT (19/11/2026)

Định dạng đầy đủ ở [`PHAN_CONG.vi.md`](../team/PHAN_CONG.vi.md), mục "Hợp đồng dữ liệu Python → Unity". Code hai phía: `python/punchar/transport/udp_sender.py` ↔ `Assets/_Project/Network/Messages.cs`. Đổi thì sửa cả hai trong cùng một PR.

| Tin | Khi nào gửi | Nội dung chính |
|---|---|---|
| `pose` | Mỗi frame đã xử lý, kể cả khi không thấy tay | `frame`, mỗi tay: `hand`, `x`, `y`, `size`, `shape`, `score`, `lm` (63 float) |
| `strike` | Một lần mỗi cú đánh đã xác nhận | `hand`, `kind` (`PUNCH_STRAIGHT` / `BLOCK` / `OPEN_PALM`, `HOOK` tuỳ chọn), `x`, `y` |
| `hand_lost` | Một lần khi tay vắng lâu hơn `lost_grace_ms` | `hand` |

- `t` ở mọi tin là thời điểm camera chụp frame gốc (ms, Unix epoch). Python và Unity cùng máy nên **độ trễ đầu-cuối = giờ Unity lúc vẽ − `t`**.
- **Lật gương chỉ một chỗ:** ảnh lật trong `capture/camera.py`, nhãn tay sửa theo ảnh đã lật trong `recognizer/mediapipe_recognizer.py`. Unity không lật thêm.
- Toạ độ `x, y` theo quy ước viewport Unity (y hướng lên). Đổi từ quy ước MediaPipe **chỉ trong `udp_sender.py`**.
- Game tự quyết định cú đánh có trúng hình hay không (so `hand`, `kind` và vị trí với hình đang bay tới).

**Câu hỏi thảo luận**
- Hình webcam sang Unity bằng đường nào: Python gửi JPEG qua UDP/TCP, chia sẻ bộ nhớ, hay để Unity giữ camera và Python nhận frame? (Thái chốt trong Sprint 2, ghi vào "Chỗ giao nhau" của `PHAN_CONG.vi.md`.)

---

## 6. Logic quyết định hành động

Trả lời câu hỏi: **khi nào thì tính là một cú đánh, loại gì, tay nào?** Cài trong `python/punchar/decision/` (Duy), có unit test trong `python/tests/test_decision.py`.

Cú đánh ghép từ **hình dạng tay** (MediaPipe `shape` và tỉ lệ xoè ngón `r_open` tính từ landmark) + **chuyển động** qua nhiều frame (tốc độ trên mặt phẳng ảnh, tốc độ tăng của `hand_size`).

| Cử chỉ | Cách nhận diện đang cài | `kind` |
|---|---|---|
| Đấm thẳng | Tay nắm + `hand_size` tăng ≥ `punch_size_growth` (15%) trong `punch_window_ms` (150 ms): tay lao về phía camera | `PUNCH_STRAIGHT` |
| Đấm thủ | Tay nắm giữ yên (tốc độ dưới ngưỡng) liên tục ≥ `block_hold_ms` (120 ms) | `BLOCK` |
| Xoè tay | Lòng bàn tay mở + đẩy về phía camera | `OPEN_PALM` |
| Đấm móc | Chưa làm. Tuỳ chọn, cắt đầu tiên khi trễ | `HOOK` |

- Mỗi tay một state machine: `IDLE → WINDUP → STRIKE → COOLDOWN → IDLE`, thêm trạng thái `BLOCK_READY` cho đấm thủ.
- Cooldown mỗi tay `cooldown_ms` (250 ms). Mất tay ngắn do nhoè hình được bù bằng `blur_grace_ms` (60 ms). Tay vắng quá `lost_grace_ms` (300 ms) thì gửi `hand_lost`.
- Làm mượt vị trí tay bằng One Euro filter (`decision/filter.py`).
- **Mọi tham số nằm trong `config/default.toml`, tính theo ms, không theo số frame.**

**Câu hỏi thảo luận**
- Mỗi lớp lọc đều cộng thêm độ trễ (ví dụ đấm thủ phải giữ 120 ms). Trong báo cáo cần tách **latency hệ thống** (máy móc) với **latency do thiết kế** (cố ý chờ để chống nhầm).
- Đấm thẳng chỉ dựa vào `hand_size` tăng, hay dùng thêm `z` của landmark? Cần số đo trên bộ dữ liệu để chọn.

**Đề xuất**
- Ghi lại vài phiên chơi thành chuỗi `FrameResult` để làm unit test cho state machine không cần webcam (đã có `ReplayRecognizer`; đặt làm "Xong khi" ở Sprint 5).

---

## 7. Thiết kế game — ĐÃ CHỐT ý tưởng (26/10/2026)

Tham khảo: Move Fast (https://youtu.be/p1DniSBv85E?t=173). Bố cục: đường chạy ở giữa, hình bay từ xa về phía người chơi, bảng điểm/combo bên trái, thông tin level bên phải, thanh tiến độ phía trên.

### Luật chơi
- **Máy bắn** phóng các **hình** bay về phía người chơi theo lịch của level.
- Mỗi hình nằm ở **bên trái hoặc bên phải** và mang ký hiệu/màu cho biết **cử chỉ cần làm**.
- Người chơi dùng **đúng tay bên đó** + **đúng cử chỉ** khi hình tới vùng đánh → trúng, cộng điểm, tăng combo.
- Sai tay, sai cử chỉ hoặc để hình bay qua → trượt, mất combo.
- Nhạc nền chỉ để tạo không khí, **không** đồng bộ theo nhịp.
- Bàn phím giả lập cú đánh (`F` tay trái, `J` tay phải) giữ lại làm dự phòng khi không có webcam.

### Bảng ánh xạ cử chỉ v1
| Cử chỉ | Hành động trong game | Trạng thái |
|---|---|---|
| Đấm thẳng (trái/phải) | Phá hình loại "đấm" | Chốt |
| Đấm thủ (trái/phải) | Đỡ hình loại "chắn" **[Chưa chốt ý nghĩa]** | Chốt cử chỉ |
| Xoè tay (trái/phải) | Chạm/đẩy hình loại "xoè" **[Chưa chốt ý nghĩa]** | Chốt cử chỉ |
| Đấm móc | Phá hình đi từ bên sườn | Tuỳ chọn |

### Hệ thống game
- **Level:** làm trước **Level 1** hoàn chỉnh (1–2 phút, có menu và màn kết thúc, M2). Level 2 + mở khoá level bằng điểm ở Sprint 6, cắt được nếu trễ.
- Lịch phóng hình đọc từ dữ liệu level: đổi file level là đổi thứ tự và tốc độ hình bay.
- **Điểm số + combo + hệ số nhân** (như hình tham khảo: Score, Combo, Multiplier, "Amazing/Awesome").
- **Top score / bảng xếp hạng** lưu cục bộ trên máy.

### Nội dung 3D / hình ảnh
| Hạng mục | Ghi chú | Ai |
|---|---|---|
| Tay | Tay 3D (rig FBX, 15 đốt ngón) bám theo landmark trong tin `pose` | Duy |
| Hình bay tới | Mỗi loại cử chỉ một hình/màu riêng, dễ phân biệt từ xa | Duy |
| Effect | Vỡ hình khi trúng, hiệu ứng trượt | Duy |
| Máy bắn, đường chạy, vùng đánh | Đối tượng tương tác, điểm thu hút của game | Thảo |
| Khung cảnh, animation máy bắn | Màu sắc hài hoà, không rối mắt. Cắt được nếu trễ | Thảo |
| Âm thanh | Nhạc nền + âm thanh trúng/trượt | Thảo |
| Hình phản chiếu | **[Chưa chốt]** ý nghĩa cụ thể | — |
| Nền AR | Hình webcam làm nền, căn khớp cảnh 3D với hình camera | Thái |

**Câu hỏi thảo luận (còn lại)**
- Cửa sổ thời gian tính "trúng" rộng bao nhiêu ms? Cửa sổ này phải bù được latency hệ thống. Đây là chỗ nối trực tiếp giữa phần inference và cảm giác chơi.
- Chế độ debug (khung xương tay, nhãn cử chỉ, latency, FPS) bật bằng một phím, dùng để demo phần kỹ thuật. Đã có Debug HUD bên tay 3D; cần gộp vào game ở Sprint 5.
- Demo bằng bản build (.exe) hay chạy từ Unity Editor? (Sprint 6: "máy demo chạy được bằng một lệnh".)

---

## 8. Inference và hiệu năng

| Chỉ số | Ý nghĩa |
|---|---|
| Latency end-to-end | Từ lúc chụp frame đến lúc game xử lý tin. Trong phần mềm: giờ Unity − `t`. Thực tế: quay tay và màn hình bằng camera 240 FPS (Sprint 6) |
| Latency từng khâu | Capture / inference / quyết định / gửi / render |
| p50 / p95 / p99, jitter | Độ ổn định, **không chỉ báo trung bình** |
| FPS | Số frame xử lý mỗi giây |
| CPU %, RAM | Tài nguyên còn lại cho game và render |
| Độ chính xác sau tối ưu | Trade-off của từng kỹ thuật |
| Kích hoạt nhầm | Số cú đánh sai mỗi phút, tỉ lệ nhãn nhảy giữa các frame |
| Tỉ lệ đánh trúng trong game | Thảo xuất từ game, dùng chung cho báo cáo |

**Cách đo:** mỗi kỹ thuật tối ưu đo trước/sau bằng `tools/benchmark.py` trên **video quay sẵn** (không dùng webcam trực tiếp), trên máy chuẩn.

**Kỹ thuật tối ưu theo kế hoạch:**

| Sprint | Kỹ thuật |
|---|---|
| 1 (xong) | Capture luồng riêng, chỉ giữ frame mới nhất; webcam MJPG (10 → 30 FPS) |
| 4 | Giảm độ phân giải, crop vùng tay |
| 5 | Frame skipping, tự giảm chất lượng khi máy quá tải (cắt được nếu trễ); giả lập máy yếu (giới hạn 1–2 core) |
| 6 | Đo end-to-end bằng camera 240 FPS, chỉnh để đạt < 100 ms |

ONNX Runtime, OpenVINO, quantization FP16/INT8 **không làm** lúc này (gắn với model close source đã tạm bỏ).

**Câu hỏi thảo luận**
- MediaPipe đã có sẵn tracking (chỉ chạy bước tìm bàn tay khi mất dấu). Phần "frame skipping" của nhóm khác cơ chế có sẵn này ở điểm nào? Cần trả lời được khi bảo vệ.

---

## 9. Lộ trình — ĐÃ CHỐT (16/11/2026)

Chi tiết từng sprint ở [`sprints/`](../sprints/README.md). Sprint đang chạy ghi ở [`docs/README.md`](../README.md).

| Mốc | Ngày | Nội dung |
|---|---|---|
| M1 | 29/11 | Đấm tay thật trước webcam → khối trong Unity vỡ |
| M2 | 13/12 | Chơi trọn Level 1 bằng tay thật, đủ 3 cử chỉ, trên nền AR |
| M3 | 27/12 | Chốt tính năng, sau mốc này chỉ sửa lỗi |
| M4 | 10/1 | Sẵn sàng demo: bản chạy, báo cáo, slide |

Nếu trễ thì cắt theo thứ tự: đấm móc → Level 2 và mở khoá level → animation máy bắn, khung cảnh → tự giảm chất lượng khi máy quá tải. **Không cắt:** M1, M2, bảng benchmark trước/sau, bảng độ chính xác.

---

## 10. Phân công — ĐÃ CHỐT (26/10/2026)

Mỗi người phụ trách trọn một lát dọc, cả 3 đều có phần Unity. Chi tiết và "Chỗ giao nhau" ở [`PHAN_CONG.vi.md`](../team/PHAN_CONG.vi.md).

| Người | Phụ trách | Đầu ra chính |
|---|---|---|
| **Thái** | Capture, recognizer, metrics, cầu nối UDP, nền AR trong Unity | Pipeline + cầu nối + nền AR, bảng benchmark trước/sau |
| **Duy** | Decision Logic (cử chỉ), bộ dữ liệu, tay 3D, hình bay, effect | Module sinh `strike`, tay 3D + bộ hình, bảng độ chính xác |
| **Thảo** | Máy bắn, trúng/trượt, điểm, combo, level, UI, âm thanh | Game hoàn chỉnh, tỉ lệ đánh trúng trong game |

Việc chung: quay bộ dữ liệu (Duy điều phối), mỗi người viết phần báo cáo của mình, họp ghép thử Chủ nhật cuối mỗi sprint.

---

## 11. Cách làm việc chung

| Mục | Quy ước | Ở đâu |
|---|---|---|
| Repo, nhánh, PR | Mỗi việc một nhánh, merge vào `main` qua PR | [`gitflow.md`](../team/gitflow.md) |
| Đặt code | Mỗi thư mục con trong `Assets/_Project/` và `python/punchar/` có một người sở hữu | [`code-structure.md`](../team/code-structure.md) |
| Unity | Mỗi người một scene `Sandbox_<Tên>.unity`; `Main.unity` một người giữ; commit `.cs` cùng `.meta` | [`unity-workflow.md`](../team/unity-workflow.md) |
| Python | 3.12, `uv venv` + `requirements.txt`, venv ở `python/.venv` | [`AGENTS.md`](../../AGENTS.md), mục "Lệnh" |
| Tham số | `python/config/default.toml`, thời gian tính bằng ms | — |
| Quyết định | Ghi một dòng vào `DECISIONS.md`, biên bản theo mẫu | [`decisions/`](../decisions/) |
| Báo cáo tuần | Số đo và nhật ký ghi ở mục "Review" của sprint; báo cáo tuần lấy từ đó | [`weekly_report/`](../weekly_report/) |
| AI agent | Đọc [`AGENTS.md`](../../AGENTS.md) và [`PROJECT_OVERVIEW.md`](PROJECT_OVERVIEW.md). Sửa tài liệu này thì sửa luôn bản tiếng Anh | — |

---

## 12. Rủi ro

| Rủi ro | Ảnh hưởng | Cách giảm |
|---|---|---|
| Cú đấm (cử chỉ động) nhận diện sai: tay nhoè khi đấm nhanh, khó đo chiều sâu bằng 1 webcam | Game khó chơi, cảm giác "đấm không ăn" | `blur_grace_ms`, ngưỡng chỉnh được trong config, nới cửa sổ trúng. Dự phòng: chỉ cần đúng hình dạng tay (nắm/xoè) khi hình tới là tính trúng |
| Chưa có cách đưa hình webcam sang Unity (Python giữ camera) | Trễ nền AR (Sprint 3), M2 | Thái chốt phương án trong Sprint 2 |
| Căn khớp tay 3D và cảnh với hình webcam: độ sâu, FOV, gốc xương cổ tay lệch với landmark 9 | AR trông lệch | Làm sau khi có nền webcam (Sprint 3), Thái + Duy phối hợp |
| Khối lượng nội dung 3D (model, animation, effect) lớn | Thiếu thời gian cho phần đo và tối ưu | Dùng primitive / asset miễn phí, làm đủ Level 1 trước rồi mới làm đẹp; cắt theo thứ tự ở mục 9 |
| Tối ưu nhưng hệ thống không nhanh hơn rõ rệt (model đã nhanh, webcam là giới hạn ở 30 FPS) | Phần đóng góp kỹ thuật mỏng | Đo trên máy yếu giả lập. Tập trung vào latency end-to-end và độ ổn định |
| Ghép muộn, mỗi phần chạy riêng nhưng ghép lại lỗi | Trễ hạn | Hợp đồng UDP đã chốt; họp ghép thử Chủ nhật mỗi tuần |
| Ánh sáng hoặc webcam lúc demo khác lúc phát triển | Demo thất bại | Test trước tại phòng demo, chuẩn bị video dự phòng (Sprint 7) |
| Trùng lịch thi, khối lượng dồn cuối | Chất lượng thấp | Sprint 1 tuần, mốc nhỏ hằng tuần; sau M3 chỉ sửa lỗi |

---

## 13. Việc cần chốt

- [x] Tech stack / engine — Python + Unity qua UDP (16/11)
- [x] Interface `FrameResult` và danh sách tin gửi sang game — hợp đồng UDP (19/11)
- [x] Tập cử chỉ (v1) — đấm thẳng, đấm thủ, xoè tay (+ đấm móc tuỳ chọn), xem mục 7
- [x] Dạng game, luật chơi — game đấm khối kiểu Move Fast, làm Level 1 trước
- [x] Máy chuẩn để benchmark — i5-12450H, đo trên video quay sẵn
- [x] Thành viên và phân công (26/10)
- [x] Mốc thời gian, lịch họp — 8 sprint, họp Chủ nhật (16/11)
- [x] Repo, quy ước nhánh — [`gitflow.md`](../team/gitflow.md)
- [ ] Ý nghĩa "đấm thủ", "xoè tay" trong game; "hình phản chiếu"
- [ ] Tiêu chí thành công (mức tối thiểu và mức mục tiêu) + cách đo
- [ ] Bộ dữ liệu đánh giá chung: số người, số cú, điều kiện quay (Sprint 4)
- [ ] Cách đưa hình webcam sang Unity (Sprint 2)
- [ ] Cách đưa game tới người dùng: bản build hay Unity Editor (Sprint 6)
