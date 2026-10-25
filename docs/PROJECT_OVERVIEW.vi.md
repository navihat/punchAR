# TỔNG QUAN DỰ ÁN — Game đấm khối AR kiểu "Move Fast" điều khiển bằng cử chỉ tay (Inference thời gian thực)

> Bản tiếng Việt dùng cho buổi họp nhóm. Bản cho agent code: `PROJECT_OVERVIEW.md` (**chưa đồng bộ** với cập nhật 26/10/2026).
> Mục đánh dấu **[Chưa chốt]** cần quyết định trong buổi họp.
> Mỗi phần có **Câu hỏi thảo luận** (để cả nhóm trả lời) và **Đề xuất** (ý kiến ban đầu, có thể bác bỏ).
> Mọi người nên đọc trước và ghi ý kiến của mình cạnh câu hỏi trước buổi họp.

---

## ★ Đã chốt sau buổi họp 26/10/2026

**Đổi game:** bỏ ý tưởng puzzle xếp khối. Chốt làm **game phản xạ đấm khối giống Move Fast** (video tham khảo: https://youtu.be/p1DniSBv85E?t=173).

- **Luật chơi cốt lõi:** máy bắn phóng các hình (khối) bay về phía người chơi. Hình bay bên nào thì dùng **tay bên đó** đánh, đúng **cử chỉ** mà hình yêu cầu. Đánh đúng thì cộng điểm và tăng combo.
- **Nhận diện:** phân biệt **tay trái / tay phải**. Bên nào đánh bên đó.
- **Tập cử chỉ v1:** đấm thẳng, đấm thủ (đỡ), xoè tay. Đấm móc là **tuỳ chọn** (làm nếu còn thời gian).
- **Ngưỡng chấp nhận cử chỉ:** có ngưỡng riêng để quyết định một cú đánh được tính hay không (chi tiết ở mục 6).
- **Hệ thống game:** có level (làm trước **Level 1**), điểm số, top score / bảng xếp hạng, mở khoá level bằng điểm.
- **Điểm thu hút người chơi:** đối tượng tương tác (ví dụ máy bắn), điểm số → bảng xếp hạng → mở level.
- **Nội dung 3D cần làm:** tay, máy bắn, hình bay tới, hình phản chiếu, khung cảnh xung quanh, animation, effect.
- **Tiêu chí phụ:**
  - Âm thanh: **chỉ là nhạc nền**, không phụ thuộc vào nhịp (game **không** phải rhythm game, hình bay theo lịch của level, không theo beat).
  - Hình ảnh: sống động, màu sắc hài hoà, bố cục hợp lý.
- **Trọng tâm kỹ thuật giữ nguyên:** giảm độ trễ và tăng độ chính xác nhận diện cử chỉ tay.

**Còn mở sau buổi họp:**
- Tech stack: game cần mô hình 3D nên phương án Python + Pygame (mục 4) **không còn phù hợp**. Còn lại Unity hoặc Web (Three.js). **[Chưa chốt]**
- "Môi trường VR/AR" cụ thể là gì: AR trên hình webcam (PC) như ban đầu, hay có kính VR? **[Chưa chốt]**
- Mô tả chính xác tư thế "đấm thủ" và mục đích của "xoè tay" trong luật chơi. **[Chưa chốt]**
- "Hình phản chiếu" là gì: hình nhân phản chiếu động tác người chơi, hay hiệu ứng phản chiếu trên sàn/tường? **[Chưa chốt]**
- Phân công 3 người (đề xuất đã gửi trong nhóm chat).

---

## 0. Chương trình buổi họp (gợi ý ~90 phút)

| Thời lượng | Nội dung | Kết quả cần có |
|---|---|---|
| 10' | Điểm lại bối cảnh, yêu cầu của thầy, kết quả thử MediaPipe (mục 1) | Cả nhóm hiểu như nhau |
| 15' | Chốt tech stack (mục 4) | 1 lựa chọn |
| 15' | Chốt interface giữa các module (mục 5) | Định dạng dữ liệu + cách truyền |
| 20' | Game: luật chơi, màn chơi, tập cử chỉ (mục 6–7) | Bảng ánh xạ cử chỉ v1 |
| 10' | Tiêu chí thành công + cách đo (mục 2, 8) | Con số mục tiêu |
| 10' | Phân công + lộ trình + cách làm việc (mục 9–11) | Ai làm gì, hạn mốc đầu tiên |
| 10' | Rủi ro + việc cần hỏi thầy / chị (mục 12) | Danh sách câu hỏi gửi đi |

---

## 1. Bối cảnh

| Mục | Nội dung |
|---|---|
| Học phần | ED4140 — Đồ án VR/AR (ĐHBK Hà Nội) |
| Đề tài | Các kỹ thuật hỗ trợ mô hình AI đáp ứng thời gian thực trong xử lý chuỗi hình ảnh |
| Sản phẩm | Game phản xạ đấm khối kiểu Move Fast, điều khiển bằng cử chỉ tay, có AR overlay ~~(trước đây: puzzle xếp khối)~~ |
| Nền tảng demo | PC + webcam |
| Hạn | Tháng 1/2027 (cuối kỳ) |
| Kiểm chứng | Unit test + technical test (latency, FPS, độ ổn định). Không làm thực nghiệm người dùng. |
| Ngoài phạm vi | Ứng dụng phục hồi chức năng / y tế |

### Tình hình hiện tại
- Model nhận diện cử chỉ tay của chị ấy sẽ được giao sau. Chưa biết định dạng, đầu vào/đầu ra và tập cử chỉ.
- Trong lúc chờ: dùng **open source**, đã chạy thử **MediaPipe Gesture Recognizer** (xem bên dưới).
- Hệ thống phải thiết kế để **thay model mà không sửa code game**.

### Kết quả thử MediaPipe ban đầu (10/2026)
Đo trên máy dev (i5-12450H, chỉ CPU), chỉ tính thời gian model chạy:

| Cấu hình | Latency trung bình | p95 |
|---|---|---|
| Video mode, theo dõi 1 tay | ~9 ms | 12 ms |
| Video mode, cho phép 2 tay nhưng trong hình chỉ có 1 tay | ~28 ms | 42 ms |
| Image mode (không tracking giữa các frame) | ~21 ms | — |

- Có sẵn 7 cử chỉ: `Closed_Fist, Open_Palm, Pointing_Up, Thumb_Down, Thumb_Up, Victory, ILoveYou` (thêm nhãn `None`).
- Có sẵn 21 điểm landmark mỗi tay (toạ độ ảnh + toạ độ 3D theo mét), có phân biệt tay trái/phải.
- **Không có sẵn cử chỉ pinch hay xoay.** Hai cử chỉ này phải tự tính từ landmark (ví dụ khoảng cách đầu ngón cái và đầu ngón trỏ), hoặc train thêm bằng MediaPipe Model Maker.
- Độ chính xác: mới thử 4 ảnh mẫu, **chưa đủ để kết luận**. Cần bộ dữ liệu riêng của nhóm (mục 8).
- Công cụ test có sẵn trong repo: `punchar/live_test.py` (webcam, đo flicker/accuracy), `punchar/eval_dataset.py` (đánh giá trên thư mục ảnh).

**Câu hỏi thảo luận**
- Thầy có yêu cầu cụ thể nào về phần "kỹ thuật hỗ trợ thời gian thực" không? Ví dụ phải tự tối ưu model, hay chỉ cần tối ưu pipeline?
- Trọng tâm chấm điểm nằm ở game/AR hay ở inference? Điều này quyết định nhóm dồn công sức vào đâu.
- Model của chị ấy so với MediaPipe: đề tài là thay thế, so sánh, hay kết hợp hai model?

---

## 2. Mục tiêu

1. Nhận diện cử chỉ tay từ webcam theo thời gian thực.
2. Chuyển dự đoán từng frame thành hành động game ổn định (logic quyết định theo thời gian).
3. Game đấm khối chơi được (ít nhất Level 1), có AR overlay (đối tượng game vẽ lên hình camera trực tiếp).
4. Tối ưu và **đo lường** inference để toàn hệ thống phản hồi tốt khi tài nguyên CPU hạn chế.

### Tiêu chí thành công (nháp, cần chốt)
- Độ chính xác trên tập cử chỉ của dự án: ≥ 90%
- Latency end-to-end (tay cử động → game phản hồi): < 100 ms
- Tốc độ pipeline: ≥ 25 FPS trên máy dev
- Game không giật khi inference đang chạy

**Câu hỏi thảo luận**
- Độ chính xác ≥ 90% đo theo **từng frame** hay theo **từng hành động** (sau khi qua logic quyết định)? Hai cách này cho ra số rất khác nhau.
- Đo trong điều kiện nào: bao nhiêu người, ánh sáng nào, khoảng cách bao xa?
- Latency end-to-end < 100 ms đo bằng cách nào? Bản thân webcam 30 FPS đã có độ trễ ~30–60 ms trước khi phần mềm nhận được frame.
- Có thêm tiêu chí về **độ ổn định** không? Ví dụ tỉ lệ kích hoạt nhầm mỗi phút, tỉ lệ nhấp nháy nhãn (flicker).
- "Game không giật" định lượng thế nào? Ví dụ FPS render ≥ 30 và p99 thời gian mỗi frame < 50 ms.

**Đề xuất**
- Chia 2 mức: **mức tối thiểu** (bắt buộc đạt khi demo) và **mức mục tiêu** (để tối ưu hướng tới).
- Đo accuracy ở cả 2 tầng: tầng frame (đánh giá model) và tầng hành động (đánh giá trải nghiệm chơi).
- Đo latency trong phần mềm bằng timestamp ở từng khâu. Đo end-to-end thực tế bằng cách quay màn hình và tay cùng lúc bằng camera 120/240 FPS của điện thoại, rồi đếm số frame chênh lệch.

---

## 3. Phần cứng phát triển

- Acer Aspire 7 A715-76G — i5-12450H — GTX 1650 4GB VRAM — RAM 8GB
- Inference chính chạy trên **CPU**. GPU chỉ dùng để thử nghiệm.

**Câu hỏi thảo luận**
- Máy của hai thành viên còn lại cấu hình thế nào? Benchmark chính thức sẽ chạy trên máy nào?
- Demo cuối kỳ chạy trên máy nào, webcam nào? Webcam laptop và webcam rời cho kết quả khác nhau.
- Hai bạn kia có webcam để phát triển không, hay phải dùng video/dữ liệu ghi sẵn?

**Đề xuất**
- Chọn **1 máy chuẩn** để đo benchmark, các máy khác chỉ dùng để phát triển.
- RAM 8 GB khá chật nếu chạy Unity Editor + Python + trình duyệt cùng lúc. Đây là một yếu tố cần cân nhắc khi chọn tech stack.

---

## 4. Tech stack — [Chưa chốt]

> **Cập nhật 26/10/2026:** game đã chốt cần mô hình 3D, animation và effect, nên Python + Pygame bị loại. Chỉ còn so sánh **Python (AI) + Unity** và **Web (MediaPipe JS + Three.js)**. Cần chốt sớm vì phần 3D phụ thuộc vào engine.

| Lựa chọn | Ưu điểm | Nhược điểm |
|---|---|---|
| Python (OpenCV + MediaPipe + Pygame) | Một ngôn ngữ, dễ tích hợp và đo inference | Đồ họa game hạn chế |
| Web (JS + MediaPipe + Three.js/WebXR) | Chạy được PC và điện thoại, hợp với AR | Khó tối ưu inference sâu (ONNX/OpenVINO) |
| Python (AI) + Unity (game) | Game đẹp, AR mạnh | Hai ngôn ngữ, cần giao tiếp qua socket, thêm latency |

**Câu hỏi thảo luận**
- Thành viên nào đã quen với Pygame, Unity hay Three.js? Kinh nghiệm sẵn có quan trọng hơn ưu điểm lý thuyết khi chỉ còn ~3 tháng.
- Game puzzle cần đồ hoạ 2D hay 3D? Nếu chỉ là xếp khối 2D thì Pygame/OpenCV có thể đủ.
- Đề tài là về inference thời gian thực. Nếu chọn Unity, phần latency do socket có trở thành điểm yếu khi bảo vệ, hay lại là thêm một khâu để đo và tối ưu?
- Có cần chạy trên điện thoại không? Nếu không, lợi thế lớn nhất của phương án Web không còn.

**Đề xuất**
- Ưu tiên **Python + Pygame (hoặc OpenCV vẽ trực tiếp)** cho bản đầu: một ngôn ngữ, dễ đo latency toàn hệ thống, phù hợp trọng tâm đề tài.
- Dù chọn phương án nào, giữ **interface ở mục 5** độc lập với ngôn ngữ (dữ liệu dạng JSON). Khi cần đổi sang Unity thì chỉ phải thêm một lớp truyền qua UDP/WebSocket.

---

## 5. Kiến trúc hệ thống

```
Webcam ──► [1] Capture ──► [2] Recognizer ──► [3] Decision Logic ──► [4] Game + AR
               │             (thay được)       (luật theo thời gian)       ▲
               └──────────── frame gốc (làm nền AR) ──────────────────────┘
                                    │
                             [5] Đo lường (mọi khâu)
```

| # | Module | Nhiệm vụ |
|---|---|---|
| 1 | Capture | Đọc webcam ở thread riêng, chỉ giữ frame mới nhất |
| 2 | Recognizer | Nhận diện tay/cử chỉ qua interface chung. Mỗi model có một adapter |
| 3 | Decision Logic | Lọc nhiễu, ngưỡng, thời gian giữ, cooldown → sinh event game |
| 4 | Game + AR | Chỉ nhận event, không gọi model trực tiếp |
| 5 | Metrics | Ghi timestamp mọi khâu để đo latency |

### Interface giữa các module (bản nháp để thảo luận)

Đầu ra của **[2] Recognizer** mỗi frame:

```python
FrameResult:
    frame_id: int
    timestamp_ms: int          # thời điểm chụp frame (dùng để đo latency)
    hands: list[HandResult]    # 0, 1 hoặc 2 tay

HandResult:
    handedness: "Left" | "Right"
    gesture: str               # "Open_Palm", "None", ...
    score: float               # 0–1
    landmarks: list[(x, y, z)] # 21 điểm, toạ độ chuẩn hoá 0–1 theo ảnh
    world_landmarks: list[(x, y, z)]  # 21 điểm, toạ độ 3D theo mét
```

Đầu ra của **[3] Decision Logic** (đầu vào của game) là event. Với game đã chốt, đề xuất:
- `STRIKE(hand, type, x, y, strength, t_ms)`: `hand` = `Left`/`Right`, `type` = `PUNCH_STRAIGHT` / `BLOCK` / `OPEN_PALM` / `HOOK` (tuỳ chọn), `(x, y)` = vị trí tay trên màn hình, `t_ms` = timestamp frame gốc (để đo latency).
- `HAND_POSE(hand, landmarks)`: vị trí tay mỗi frame để game vẽ tay 3D.
- `HAND_LOST(hand)`: mất dấu tay.

Game tự quyết định cú đánh có trúng hình hay không (so `hand`, `type` và vị trí với hình đang bay tới).

**Câu hỏi thảo luận**
- Landmark 21 điểm có đưa thẳng cho game không, hay game chỉ nhận event? Nếu vẽ bàn tay ảo trong AR thì game cần landmark.
- Toạ độ đã lật gương hay chưa? Lật ở khâu nào? Nên chốt **một chỗ duy nhất**.
- Khi không thấy tay, hoặc tay biến mất giữa lúc đang cầm khối, game xử lý thế nào?
- Model của chị ấy có thể không trả landmark, chỉ trả nhãn cử chỉ. Khi đó con trỏ lấy vị trí từ đâu? Adapter có cần chạy kèm MediaPipe để lấy vị trí tay không?
- Pinch và xoay tính ở **[2]** (coi như một "cử chỉ") hay ở **[3]** (luật trên landmark)?
- Các module truyền dữ liệu cho nhau thế nào: gọi hàm, queue giữa các thread, hay socket?

**Đề xuất**
- **[2]** chỉ trả kết quả thô từng frame. Mọi luật theo thời gian (giữ, cooldown, hysteresis) nằm ở **[3]**.
- Làm sớm một **mock recognizer** phát lại kết quả đã ghi sẵn từ file. Người làm logic và game dùng nó để phát triển mà không cần webcam và không phải chờ inference.
- Chốt interface xong thì **đóng băng** nó. Muốn thay đổi phải báo cả nhóm.

---

## 6. Logic quyết định hành động

Trả lời câu hỏi: **khi nào thì tính là một cú đánh, loại gì, tay nào?** (đây chính là "ngưỡng chấp nhận cử chỉ tay" đã chốt)

**Lưu ý quan trọng:** đấm thẳng và đấm móc là cử chỉ **động** (có chuyển động), MediaPipe Gesture Recognizer chỉ nhận cử chỉ **tĩnh** (`Closed_Fist`, `Open_Palm`...). Vì vậy cú đấm phải ghép từ **hình dạng tay** (nắm/xoè) + **chuyển động** tính từ landmark qua nhiều frame.

| Cử chỉ | Cách nhận diện đề xuất |
|---|---|
| Đấm thẳng | Tay nắm (`Closed_Fist`) + kích thước bàn tay trên ảnh tăng nhanh (tay lao về phía camera) trong một cửa sổ thời gian ngắn |
| Đấm móc (tuỳ chọn) | Tay nắm + vận tốc ngang lớn, hướng vào giữa màn hình |
| Đấm thủ (đỡ) | Tay nắm giữ yên trước mặt trong một khoảng thời gian **[cần mô tả tư thế]** |
| Xoè tay | `Open_Palm` (có sẵn trong MediaPipe), có thể kèm đẩy tay ra trước |

Các ngưỡng:
- **Ngưỡng confidence:** bỏ dự đoán hình dạng tay dưới ngưỡng (ví dụ 0.7).
- **Ngưỡng tốc độ / biên độ:** tay phải di chuyển đủ nhanh và đủ xa mới tính là đấm (tránh kích hoạt khi chỉ đưa tay lên).
- **Ngưỡng theo kích thước bàn tay:** chuẩn hoá tốc độ theo kích thước tay để không phụ thuộc khoảng cách đến camera.
- **Cooldown mỗi tay:** khoảng nghỉ tối thiểu giữa hai cú của cùng một tay (ví dụ 200–300 ms).
- **Làm mượt:** làm mượt vị trí tay để vẽ tay 3D (One Euro filter).

Triển khai bằng **state machine cho từng tay**: `IDLE → WINDUP (tay nắm, bắt đầu lao) → STRIKE (phát event) → COOLDOWN → IDLE`. Mọi tham số để trong file config.

**Câu hỏi thảo luận**
- Thời gian giữ tính theo **số frame** hay **mili giây**? Nếu FPS thay đổi (máy yếu, đang tối ưu) thì tính theo frame sẽ làm thay đổi cảm giác chơi.
- Mỗi lớp lọc đều cộng thêm độ trễ (ví dụ giữ 5 frame ở 30 FPS ≈ 170 ms). Như vậy có mâu thuẫn với mục tiêu latency < 100 ms không?
- Tay đấm nhanh dễ bị **nhoè hình (motion blur)** và mất tracking đúng lúc ra đòn. Khi đó vẫn tính cú đấm dựa trên các frame trước đó được không?
- Đấm thẳng về phía camera: chỉ dựa vào kích thước tay tăng, hay dùng thêm toạ độ `z` của landmark? Cần thử xem cái nào ổn định hơn.
- Kiểm thử logic thế nào khi không có người ngồi trước webcam? Dùng chuỗi FrameResult ghi sẵn làm unit test được không?

**Đề xuất**
- Tham số thời gian tính theo **ms**, không theo số frame.
- Tách rõ hai loại latency trong báo cáo: **latency hệ thống** (máy móc) và **latency do thiết kế** (cố ý giữ/lọc để chống nhầm).
- Ghi lại vài phiên chơi thành file để làm unit test cho state machine.

---

## 7. Thiết kế game — ĐÃ CHỐT ý tưởng (26/10/2026)

Tham khảo: Move Fast (https://youtu.be/p1DniSBv85E?t=173). Hình tham khảo cho thấy bố cục: đường chạy ở giữa, hình bay từ xa về phía người chơi, bảng điểm/combo bên trái, thông tin bài/level bên phải, thanh tiến độ phía trên.

### Luật chơi
- **Máy bắn** phóng các **hình** bay về phía người chơi theo lịch của level.
- Mỗi hình nằm ở **bên trái hoặc bên phải** và mang ký hiệu/màu cho biết **cử chỉ cần làm**.
- Người chơi dùng **đúng tay bên đó** + **đúng cử chỉ** khi hình tới vùng đánh → trúng, cộng điểm, tăng combo.
- Sai tay, sai cử chỉ hoặc để hình bay qua → trượt, mất combo.
- Nhạc nền chỉ để tạo không khí, **không** đồng bộ theo nhịp.

### Bảng ánh xạ cử chỉ v1
| Cử chỉ | Hành động trong game | Trạng thái |
|---|---|---|
| Đấm thẳng (trái/phải) | Phá hình loại "đấm" | Chốt |
| Đấm thủ (trái/phải) | Đỡ hình loại "chắn" **[cần chốt ý nghĩa]** | Chốt cử chỉ |
| Xoè tay (trái/phải) | Chạm/đẩy hình loại "xoè" **[cần chốt ý nghĩa]** | Chốt cử chỉ |
| Đấm móc | Phá hình đi từ bên sườn | Tuỳ chọn |

### Hệ thống game
- **Level:** làm trước **Level 1** hoàn chỉnh. Level sau khó hơn bằng: hình bay nhanh hơn, dày hơn, trộn nhiều loại cử chỉ hơn.
- **Điểm số + combo + hệ số nhân** (như hình tham khảo: Score, Combo, Multiplier, "Amazing/Awesome").
- **Top score / bảng xếp hạng** (lưu cục bộ trên máy là đủ cho demo).
- **Mở khoá level** khi đạt đủ điểm ở level trước.

### Nội dung 3D / hình ảnh
| Hạng mục | Ghi chú |
|---|---|
| Tay | Tay 3D bám theo landmark của người chơi |
| Máy bắn | Đối tượng tương tác, điểm thu hút của game |
| Hình bay tới | Mỗi loại cử chỉ một hình/màu riêng, dễ phân biệt từ xa |
| Hình phản chiếu | **[Chưa chốt]** ý nghĩa cụ thể |
| Khung cảnh xung quanh | Màu sắc hài hoà, không làm rối mắt khi chơi |
| Animation | Máy bắn, hình bay, tay |
| Effect | Vỡ hình khi trúng, chữ combo, hiệu ứng trượt |
| Âm thanh | Nhạc nền + âm thanh trúng/trượt |

**Câu hỏi thảo luận (còn lại)**
- Một màn kéo dài bao lâu? Đấm liên tục rất mỏi, đề xuất 1–2 phút mỗi màn.
- Cửa sổ thời gian để tính "trúng" rộng bao nhiêu ms? Cửa sổ này phải bù được latency của hệ thống. Đây là chỗ nối trực tiếp giữa phần inference và cảm giác chơi.
- Có chế độ debug hiện khung xương bàn tay, nhãn cử chỉ, latency không? (Đề xuất: có, bật bằng 1 phím, dùng để demo phần kỹ thuật.)
- Người thuận tay trái có cần chế độ riêng không? (Luật "bên nào đánh bên đó" đã khá cân bằng.)
- Demo bằng file chạy (.exe), lệnh, hay trang web? Phụ thuộc tech stack.

---

## 8. Inference và hiệu năng

Không chỉ đo latency:

| Chỉ số | Ý nghĩa |
|---|---|
| Latency end-to-end | Từ lúc chụp frame đến lúc game xử lý event |
| Latency từng khâu | Capture / tiền xử lý / inference / quyết định / render |
| p50 / p95 / p99, jitter | Độ ổn định, không chỉ trung bình |
| FPS | Số frame xử lý mỗi giây |
| CPU %, RAM | Tài nguyên còn lại cho game và render |
| Accuracy sau tối ưu | Trade-off của từng kỹ thuật |
| Flicker / kích hoạt nhầm | Tỉ lệ nhãn nhảy giữa các frame, số hành động sai mỗi phút |

Kỹ thuật tối ưu sẽ thử (đo trước và sau mỗi kỹ thuật): ONNX Runtime, OpenVINO, quantization FP16/INT8, giảm độ phân giải, crop vùng tay, frame skipping + tracking, chạy song song các khâu.

**Giả lập thiết bị yếu trên laptop:** giới hạn 1–2 core, chế độ tiết kiệm pin, giảm độ phân giải camera.

Thiết bị nhỏ mục tiêu (camera / điện thoại): **[Chưa chốt]**, không bắt buộc cho demo PC.

**Câu hỏi thảo luận**
- Bộ dữ liệu đánh giá chung: bao nhiêu người quay, mỗi cử chỉ bao nhiêu giây, những điều kiện nào (sáng/tối, gần/xa, nền rối)? Ai phụ trách quay và gán nhãn?
- Nên dùng **video quay sẵn** để benchmark thay vì webcam trực tiếp, để mọi lần đo so sánh được với nhau?
- MediaPipe đóng gói model dạng `.task` (TFLite). Chuyển sang ONNX/OpenVINO tốn công đáng kể. Có đáng làm không, hay để dành các kỹ thuật này cho model của chị ấy?
- MediaPipe đã có sẵn tracking (chỉ chạy bước tìm bàn tay khi mất dấu). Phần "frame skipping + tracking" của nhóm khác với cơ chế có sẵn này ở điểm nào?
- Bao nhiêu kỹ thuật tối ưu là đủ cho báo cáo? Đề xuất chọn 3–4 kỹ thuật làm kỹ (đo đầy đủ trade-off) thay vì nhiều kỹ thuật làm nông.
- Inference và game có chạy chung tiến trình không? Python có GIL, nên có thể cần tách tiến trình để game không giật.

**Đề xuất**
- Viết sớm `benchmark.py` chạy trên video chuẩn, xuất bảng p50/p95/p99, FPS, CPU%. Mọi kỹ thuật tối ưu đều đo bằng script này.
- Thứ tự thử: (1) chạy song song capture và inference, (2) giảm độ phân giải, (3) chỉnh tracking và số tay, (4) giả lập máy yếu. Lượng tử hoá và đổi runtime để sau khi đã có model của chị ấy.

---

## 9. Lộ trình

| Giai đoạn | Công việc | Kết quả |
|---|---|---|
| 1 | Chạy open source, đánh giá độ chính xác trên tập cử chỉ | Quyết định dùng hay không + báo cáo test |
| 2 | Logic quyết định (state machine) | Chuỗi event game từ webcam |
| 3 | Thiết kế game + AR (song song với 1–2) | Prototype chơi được |
| 4 | Đo lường + tối ưu inference | Bảng benchmark |
| 5 | Tích hợp model của chị ấy qua adapter | So sánh với baseline |
| 6 | Kiểm thử, demo, báo cáo | Nộp cuối kỳ (1/2027) |

**Câu hỏi thảo luận**
- Gắn ngày cụ thể cho từng giai đoạn. Từ nay đến 1/2027 còn khoảng 12 tuần, trừ thời gian thi.
- Mốc **"chạy được toàn bộ từ webcam đến game"** (dù rất thô) đặt ở tuần mấy? Đề xuất: tuần 3–4.
- Nếu đến giữa 12/2026 vẫn chưa nhận được model của chị ấy thì sao? Có phương án dự phòng (chỉ báo cáo với MediaPipe) không?
- Bao lâu họp một lần? Báo tiến độ qua đâu (Zalo, Messenger, GitHub Issues)?
- Báo cáo cuối kỳ ai viết phần nào? Có nên viết dần theo từng giai đoạn không?

---

## 10. Phân công (đề xuất cho 3 người) — [Chưa chốt]

| Vai trò | Phụ trách | Đầu ra chính |
|---|---|---|
| **Inference** | Capture, Recognizer + adapter, Metrics, tối ưu | Module nhận diện theo interface mục 5, `benchmark.py`, bảng benchmark |
| **Logic** | Decision Logic, state machine, config, unit test | Module sinh event từ FrameResult, bộ test bằng dữ liệu ghi sẵn |
| **Game + AR** | Luật chơi, màn chơi, render, AR overlay, UI | Game chạy được với mock recognizer, sau đó với recognizer thật |

Việc chung: quay bộ dữ liệu đánh giá, tích hợp, viết báo cáo, chuẩn bị demo.

**Câu hỏi thảo luận**
- Ai nhận vai trò nào? Vai trò Logic khá nhẹ: có nên ghép với phần test và tích hợp, hoặc chia sang viết báo cáo?
- Ai là người **tích hợp** cuối cùng, chịu trách nhiệm toàn bộ hệ thống chạy được?
- Ai giữ liên lạc với thầy và với chị ấy?

---

## 11. Cách làm việc chung

**Câu hỏi thảo luận**
- Dùng GitHub/GitLab repo chung? Quy ước nhánh như thế nào (mỗi người một nhánh, merge qua Pull Request)?
- Cấu trúc thư mục: mỗi module một thư mục riêng (`capture/`, `recognizer/`, `logic/`, `game/`, `metrics/`)?
- Chốt phiên bản Python và cách quản lý thư viện (`requirements.txt`, `uv`) để máy ai cũng chạy được.
- Tham số (ngưỡng, thời gian giữ, cooldown) để chung trong một file config như `config.yaml`?
- Nhóm có dùng AI agent viết code không? Nếu có, giữ `PROJECT_OVERVIEW.md` luôn đồng bộ với bản tiếng Việt này.

---

## 12. Rủi ro

| Rủi ro | Ảnh hưởng | Cách giảm |
|---|---|---|
| Model của chị ấy đến muộn hoặc khác định dạng | Giai đoạn 5 bị dồn | Adapter + mock. Báo cáo được với MediaPipe làm baseline |
| Cú đấm (cử chỉ động) nhận diện sai: tay nhoè khi đấm nhanh, khó đo chiều sâu bằng 1 webcam | Game khó chơi, cảm giác "đấm không ăn" | Nới cửa sổ trúng, ngưỡng chỉnh được trong config. Dự phòng: chỉ cần đúng hình dạng tay (nắm/xoè) khi hình tới là tính trúng |
| Khối lượng nội dung 3D (model, animation, effect) lớn so với 3 tháng | Trễ hạn, thiếu thời gian cho phần inference | Dùng asset miễn phí, làm đủ Level 1 trước rồi mới làm đẹp |
| Chưa chốt engine nên phần 3D chưa bắt đầu được | Dồn việc | Chốt tech stack trong tuần này |
| Tối ưu inference nhưng hệ thống không nhanh hơn rõ rệt (model vốn đã nhanh, ~9 ms) | Phần đóng góp kỹ thuật mỏng | Đo trên máy yếu giả lập. Tập trung vào latency end-to-end và độ ổn định |
| Tích hợp muộn, mỗi phần chạy riêng nhưng ghép lại lỗi | Trễ hạn | Chốt interface sớm, ghép bản thô từ tuần 3–4 |
| Ánh sáng hoặc webcam lúc demo khác lúc phát triển | Demo thất bại | Test trước tại phòng demo, chuẩn bị video dự phòng |
| Tranh thủ học kỳ thi, khối lượng dồn cuối | Chất lượng thấp | Đặt mốc nhỏ hằng tuần |

---

## 13. Việc cần chốt trong buổi họp

- [ ] Tech stack / engine
- [ ] Interface `FrameResult` và danh sách event game
- [x] Tập cử chỉ và bảng ánh xạ hành động (v1) — đấm thẳng, đấm thủ, xoè tay (+ đấm móc tuỳ chọn), xem mục 7
- [x] ~~Dạng puzzle~~ Dạng game, các màn chơi và luật chơi — game đấm khối kiểu Move Fast, làm Level 1 trước
- [ ] Cách đưa game tới người dùng
- [ ] Tiêu chí thành công (mức tối thiểu và mức mục tiêu) + cách đo
- [ ] Máy chuẩn để benchmark và bộ dữ liệu đánh giá chung
- [ ] Thành viên và phân công, người tích hợp
- [ ] Mốc thời gian cụ thể, lịch họp, kênh liên lạc
- [ ] Repo, quy ước nhánh

### Cần hỏi người khác (sau buổi họp)
- **Chị ấy:** model định dạng gì (PyTorch/ONNX/TFLite)? Đầu vào là ảnh cả khung hình hay ảnh đã cắt vùng tay? Đầu ra là nhãn hay có landmark? Tập cử chỉ gồm những gì? Khi nào giao?
- **Thầy:** "camera" ở yêu cầu thiết bị nhỏ là thiết bị gì? Trọng tâm chấm là inference hay sản phẩm game? Có cần so sánh nhiều model không?

---

## Biên bản họp

| Ngày | Quyết định | Người phụ trách | Hạn |
|---|---|---|---|
| 26/10/2026 | Bỏ puzzle, chốt game đấm khối kiểu Move Fast | Cả nhóm | — |
| 26/10/2026 | Nhận diện tay trái/phải, bên nào đánh bên đó. Cử chỉ: đấm thẳng, đấm thủ, xoè tay (đấm móc tuỳ chọn). Có ngưỡng chấp nhận cử chỉ | Cả nhóm | — |
| 26/10/2026 | Game có level (Level 1 trước), top score, bảng xếp hạng, mở level | Cả nhóm | — |
| 26/10/2026 | Âm thanh chỉ là nhạc nền, không theo nhịp. Hình ảnh sống động, màu hài hoà | Cả nhóm | — |
| 26/10/2026 | Phân công 3 người: đề xuất đã gửi nhóm chat, chờ xác nhận | | |
