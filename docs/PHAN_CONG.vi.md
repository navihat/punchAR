# PHÂN CÔNG — Game đấm khối AR

> Duyệt ngày 26/10/2026. Bối cảnh dự án và các quyết định đã chốt: `PROJECT_OVERVIEW.md`.

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

## 🤝 Việc chung
- Cả nhóm quay bộ dữ liệu (Duy điều phối)
- Mỗi người viết phần báo cáo của mình
- Tích hợp: họp ghép thử cuối mỗi giai đoạn, cả 3 cùng có mặt

---

## ⏰ Mốc

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
