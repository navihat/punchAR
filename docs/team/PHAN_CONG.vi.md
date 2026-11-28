# PHÂN CÔNG — Game đấm khối AR

> Duyệt ngày 26/10/2026. Bối cảnh dự án: [`PROJECT_OVERVIEW.vi.md`](../planning/PROJECT_OVERVIEW.vi.md). Quyết định đã chốt: [`DECISIONS.md`](../decisions/DECISIONS.md).

**Cách chia:** mỗi người phụ trách **trọn một lát** từ đầu đến cuối, không chia "người làm AI / người làm game". Như vậy không ai bị dồn việc, và cả 3 người đều có phần VR/AR để trình bày.

---

## 👤 Người 1 (Thái): Pipeline thời gian thực + AR
*Từ webcam đến hình hiện trong Unity, nhanh nhất có thể.*

**Python**
- Capture chạy luồng riêng, chỉ giữ frame mới nhất. Chỉnh webcam (MJPG, FPS, buffer)
- Chạy MediaPipe 2 tay. Tối ưu: giảm độ phân giải, crop vùng tay, frame skipping, tự giảm chất lượng khi máy quá tải
- `benchmark.py` chạy trên video quay sẵn, giả lập máy yếu

**Unity**
- Cầu nối UDP cả hai đầu (Python gửi, C# nhận)
- **Lớp AR:** đưa hình webcam vào Unity làm nền, căn khớp cảnh 3D với hình camera

**Đo:** độ trễ từng khâu và end-to-end (quay bằng camera 240 FPS)

**Sau này:** tích hợp model close source có sẵn qua adapter, thử ONNX / quantization

**Đầu ra:** pipeline + cầu nối + nền AR, bảng benchmark trước/sau.

---

## 👤 Người 2 (Duy): Cử chỉ tay, từ nhận diện đến bàn tay trong game
*Mọi thứ liên quan đến "tay người chơi làm gì và game thấy gì".*

**Python**
- Phân biệt tay trái/phải theo góc nhìn người chơi
- Nhận cú đánh từ chuỗi landmark: đấm thẳng → đấm thủ → xoè tay → đấm móc (nếu kịp)
- State machine từng tay, ngưỡng chấp nhận cử chỉ, cooldown, config. Làm mượt và dự đoán quỹ đạo tay
- Quay bộ dữ liệu cú đánh, đo độ chính xác và tỉ lệ kích hoạt nhầm, unit test

**Unity**
- **Tay 3D** đi theo landmark của người chơi
- **Thiết kế hình bay tới:** mỗi cử chỉ một hình/màu, nhìn là biết phải đánh kiểu gì
- Effect khi trúng (vỡ hình) / trượt
- Chế độ debug: khung xương tay, nhãn cử chỉ

**Đầu ra:** module sinh `strike`, tay 3D + bộ hình, bảng độ chính xác.

---

## 👤 Người 3 (Thảo): Gameplay + thế giới game
*Game chơi được và đẹp.*

**Unity**
- Đường chạy, máy bắn, lịch phóng hình theo level, vùng đánh, kiểm tra trúng/trượt
- Bàn phím giả lập cú đánh để làm song song từ tuần đầu
- Điểm, combo, hệ số nhân, thanh tiến độ, UI (bảng điểm, menu)
- Level 1 hoàn chỉnh → Level 2+, top score, bảng xếp hạng, mở khoá level
- Khung cảnh xung quanh, animation máy bắn, nhạc nền + âm thanh trúng/trượt

**Đầu ra:** game hoàn chỉnh, tỉ lệ đánh trúng trong game (số liệu này dùng chung với Thái, Duy).

---

## 🔗 Chỗ giao nhau (cần thống nhất sớm)

| Giữa | Thống nhất cái gì |
|---|---|
| Thái ↔ Duy | Định dạng `FrameResult`, ai chạy MediaPipe (Thái), ai đọc kết quả (Duy) |
| Thái ↔ Thảo | Định dạng tin UDP, hệ toạ độ Unity, nền AR đặt ở đâu trong cảnh |
| Duy ↔ Thảo | Tên loại cú đánh (`PUNCH_STRAIGHT`...), hình nào ứng với cử chỉ nào, độ rộng vùng đánh |

### Hợp đồng dữ liệu Python → Unity

> **Đã chốt 19/11/2026 (Thái).** Đổi bất cứ thứ gì ở đây phải sửa cả `python/punchar/transport/udp_sender.py` và `Assets/_Project/Network/Messages.cs` trong cùng một PR, cả 3 người đồng ý.

**Đường truyền:** UDP tới `127.0.0.1:5005`, chỉ một chiều Python → Unity. Mỗi gói tin là **một object JSON** (UTF-8, không xuống dòng). Mất gói thì bỏ qua, không gửi lại.

**Cách Unity đọc:** parse trước thành `BaseMessage` để lấy `type`, rồi parse lại thành đúng class. Gặp `type` lạ thì **bỏ qua**, không báo lỗi.

#### Quy ước chung

| Mục | Quy ước |
|---|---|
| `t` | Thời điểm **camera chụp** frame gốc, tính bằng **ms theo Unix epoch** (`time.time_ns() // 1_000_000` bên Python, `DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()` bên Unity). Python và Unity chạy cùng máy nên chung đồng hồ: **độ trễ đầu-cuối = giờ Unity lúc vẽ − `t`** |
| Tay `hand` | `"Left"` hoặc `"Right"`, viết đúng hoa/thường, theo **tay thật của người chơi**. Giơ tay phải là `"Right"` |
| Lật gương | Ảnh đã được lật **một lần duy nhất** trong `capture/camera.py`. Ảnh lật trông như soi gương: tay phải nằm bên phải màn hình. Unity **không lật thêm** |
| Toạ độ `x, y` | Chuẩn hoá 0–1 theo **ảnh webcam đã lật**, cùng quy ước với viewport của Unity: `x` = 0 ở mép trái, 1 ở mép phải; `y` = 0 ở mép **dưới**, 1 ở mép **trên**. Python đổi từ quy ước của MediaPipe (y hướng xuống) sang quy ước này **trong `udp_sender.py`**, Unity dùng thẳng. Nếu nền webcam phủ đúng toàn màn hình thì đưa thẳng vào `Camera.ViewportToWorldPoint` được |
| Độ sâu `z` | `z` của MediaPipe giữ nguyên: độ sâu tương đối so với cổ tay, cùng thang với `x`, **âm là gần camera hơn**. Chỉ dùng để dựng hình tay 3D, không dùng làm khoảng cách thật |
| Số thực | Làm tròn 4 chữ số thập phân |

#### Tin `pose`: vị trí tay, gửi mỗi frame

Gửi **mỗi frame đã xử lý** (~30 lần/giây), kể cả khi không thấy tay (`hands` rỗng). Nhờ vậy Unity biết pipeline vẫn đang chạy.

```json
{"type":"pose","t":1795072926644,"frame":1532,
 "hands":[{"hand":"Right","x":0.7312,"y":0.5979,"size":0.1830,
           "shape":"Closed_Fist","score":0.9312,
           "lm":[0.7101,0.4520,0.0,  0.7350,0.4811,-0.0123,  ...]}]}
```

| Trường | Kiểu | Ý nghĩa |
|---|---|---|
| `frame` | int | Số thứ tự frame, tăng dần. Dùng để phát hiện mất gói |
| `hands` | mảng 0–2 phần tử | Các tay thấy trong frame này |
| `hand` | string | `"Left"` / `"Right"` |
| `x`, `y` | float | Vị trí tâm bàn tay (landmark 9, gốc ngón giữa). Dùng cho con trỏ, vị trí cú đánh |
| `size` | float | Kích thước tay trên ảnh: khoảng cách landmark 0 → 9 tính trong toạ độ chuẩn hoá (giống `hand_size()` trong `decision/state_machine.py`). Tay càng gần camera số càng lớn |
| `shape` | string | Hình dạng tay MediaPipe nhận được: `Closed_Fist`, `Open_Palm`, `Pointing_Up`, `Thumb_Up`, `Thumb_Down`, `Victory`, `ILoveYou`, hoặc `None` |
| `score` | float 0–1 | Độ tin cậy của `shape` |
| `lm` | 63 float | **21 landmark** nối liền: `[x0,y0,z0, x1,y1,z1, ..., x20,y20,z20]`, cùng quy ước toạ độ ở trên. Thứ tự điểm: 0 cổ tay; 1–4 ngón cái; 5–8 ngón trỏ; 9–12 ngón giữa; 13–16 ngón áp út; 17–20 ngón út. Dùng mảng phẳng vì `JsonUtility` không đọc được mảng lồng nhau |

Tay **không có trong `hands`** ở một frame chỉ có nghĩa là frame đó không thấy tay, **chưa phải mất tay**. Mất tay thật thì chờ tin `hand_lost`.

#### Tin `strike`: một cú đánh đã được xác nhận

Gửi **một lần** cho mỗi cú đánh, ngay khi Decision Logic xác nhận. Unity tự quyết định trúng hay trượt (so `hand`, `kind`, vị trí với hình đang bay tới).

```json
{"type":"strike","t":1795072926711,"hand":"Left","kind":"PUNCH_STRAIGHT","x":0.3120,"y":0.5521}
```

| Trường | Kiểu | Ý nghĩa |
|---|---|---|
| `t` | long | Thời điểm chụp **frame xác nhận** cú đánh |
| `hand` | string | `"Left"` / `"Right"` |
| `kind` | string | `PUNCH_STRAIGHT` (đấm thẳng), `BLOCK` (đấm thủ), `OPEN_PALM` (xoè tay), `HOOK` (đấm móc, tuỳ chọn, chưa làm) |
| `x`, `y` | float | Vị trí tâm bàn tay lúc xác nhận |

#### Tin `hand_lost`: mất dấu tay

Gửi **một lần** khi một tay vắng mặt liên tục lâu hơn `lost_grace_ms` (trong `config/default.toml`). Tay xuất hiện lại thì cứ thế có trong tin `pose`, không có tin riêng.

```json
{"type":"hand_lost","t":1795072927010,"hand":"Right"}
```

`t` là thời điểm chụp frame **cuối cùng còn thấy tay**.

#### Kênh ảnh webcam (nền AR): bản thử 28/11/2026 (Thái), chưa chốt

Python giữ camera nên Unity không mở trực tiếp được; Python gửi luôn ảnh sang. Kênh riêng, không ảnh hưởng 3 tin JSON ở trên.

| Mục | Quy ước |
|---|---|
| Đường truyền | UDP tới `127.0.0.1:5006` (`[video]` trong `config/default.toml`), Python → Unity. Mỗi frame **một gói**, mất gói thì bỏ qua |
| Gói tin | 12 byte đầu (little-endian): `int32 frame`, `int64 t`; phần còn lại là ảnh **JPEG** |
| `frame`, `t` | Giống hệt tin `pose` của cùng frame. Python gửi ảnh **sau** tin `pose`, để nền và tay 3D cùng một frame |
| Ảnh | 640×360, chất lượng 80, **đã lật gương** (như toạ độ `x, y`). Unity hiện nguyên, phủ toàn màn hình nên `x, y` của `pose` khớp với ảnh |
| Code | `python/punchar/transport/frame_sender.py` ↔ `Assets/_Project/AR/WebcamBackground.cs` |

#### Code theo hợp đồng

| File | Thay đổi | Ai |
|---|---|---|
| `python/punchar/capture/camera.py` | `timestamp_ms` lấy theo Unix epoch thay vì `time.monotonic()` | Thái, đã xong |
| `python/punchar/transport/udp_sender.py` | Đổi `y` → `1 − y`; thêm `frame`, `size`, `score`, `lm` vào `pose` | Thái, đã xong |
| `Assets/_Project/Network/Messages.cs` | Thêm `frame` vào `PoseMessage`; thêm `size`, `score`, `lm` (`float[]`) vào `HandPose` | Thái, đã xong |
| `python/punchar/decision/state_machine.py` | Gửi `hand_lost` (đang là `TODO`) | Duy, chưa làm |

## 🤝 Việc chung
- Cả nhóm quay bộ dữ liệu (Duy điều phối)
- Mỗi người viết phần báo cáo của mình
- Tích hợp: họp ghép thử cuối mỗi giai đoạn, cả 3 cùng có mặt

---

## ⏰ Mốc

> Lịch cũ, đã thay bằng [kế hoạch sprint](../sprints/README.md) từ 16/11/2026.

| Giai đoạn | Thời gian | N1 (Thái) | N2 (Duy) | N3 (Thảo) |
|---|---|---|---|---|
| 1. Nền móng | 27/10 – 8/11 | Baseline 2 tay, capture luồng riêng, UDP gửi được tin tới Unity | Nhận đấm thẳng + trái/phải (vẽ bằng OpenCV) | Học Unity, khối bay tới, đánh bằng bàn phím |
| 2. Ghép bản thô | 9/11 – 22/11 | Nền webcam trong Unity, `benchmark.py` | Tay 3D bám theo tay thật, bộ hình bản đầu | Điểm, combo, UI cơ bản |
| **Mốc 22/11** | | | | **Đấm tay thật trước webcam → khối trong Unity vỡ, có nền AR** |
| 3. Tối ưu + hoàn thiện | 23/11 – 20/12 | Các kỹ thuật tối ưu + bảng trước/sau, đo end-to-end | Đủ 3 cử chỉ, bộ dữ liệu, bảng độ chính xác, effect | Level 1 hoàn chỉnh, khung cảnh, âm thanh, bảng xếp hạng |
| 4. Hoàn thiện + báo cáo | 21/12 – 1/2027 | Tích hợp model close source + so sánh với MediaPipe | Đấm móc (nếu kịp), debug mode | Level 2+, mở khoá level |

---

## ❓ Cần chốt thêm
- "Đấm thủ" là tư thế nào? "Xoè tay" dùng để làm gì trong game? "Hình phản chiếu" là gì?
