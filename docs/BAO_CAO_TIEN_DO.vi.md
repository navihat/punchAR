# BÁO CÁO TIẾN ĐỘ — Game đấm khối AR điều khiển bằng cử chỉ tay

> Học phần ED4140 — Đồ án VR/AR · Nhóm: Thái, Duy, Thảo · Cập nhật: 30/10/2026

## 1. Đề tài và sản phẩm

**Đề tài:** Các kỹ thuật hỗ trợ mô hình AI đáp ứng thời gian thực trong xử lý chuỗi hình ảnh.

**Sản phẩm minh hoạ:** game phản xạ trên PC + webcam (tham khảo lối chơi của *Move Fast*). Máy bắn phóng các hình bay về phía người chơi. Hình bay bên nào thì người chơi dùng **tay bên đó**, làm **đúng cử chỉ** hình yêu cầu để phá hình, ghi điểm và tăng combo. Đối tượng 3D được vẽ chồng lên hình webcam (AR).

- Cử chỉ: **đấm thẳng, đấm thủ (đỡ), xoè tay**; đấm móc làm thêm nếu còn thời gian.
- Hệ thống game: Level 1 trước, sau đó thêm level, điểm/combo, bảng xếp hạng, mở khoá level.
- Ngoài phạm vi: thực nghiệm người dùng, ứng dụng y tế.

**Trọng tâm kỹ thuật:** giảm độ trễ và tăng độ chính xác, độ ổn định của nhận diện cử chỉ tay. Game là nơi kiểm chứng các kỹ thuật này.

## 2. Mục tiêu đo được (bản nháp)

| Chỉ số | Mục tiêu |
|---|---|
| Độ chính xác nhận diện cú đánh | ≥ 90% |
| Độ trễ end-to-end (tay cử động → game phản hồi) | < 100 ms |
| Tốc độ pipeline | ≥ 25 FPS trên laptop chỉ dùng CPU |
| Độ ổn định | Đo thêm tỉ lệ kích hoạt nhầm và nhấp nháy nhãn |

Máy đo chuẩn: laptop i5-12450H, 8 GB RAM, inference chạy trên CPU.

## 3. Hướng tiếp cận

**Công nghệ:** Python (nhận diện, AI) + Unity (game 3D, AR), hai bên trao đổi qua UDP.

```
Webcam → Capture → Recognizer → Logic quyết định → (UDP) → Unity: game + AR
                    (thay được)   (ngưỡng, thời gian)
              Đo thời gian ở mọi khâu để tính độ trễ
```

- **Recognizer thay được:** hiện dùng MediaPipe (open source) làm baseline. Sau đó sẽ tích hợp một model nhận diện close source có sẵn bằng cách viết thêm adapter, không phải sửa game.
- **Logic quyết định:** MediaPipe chỉ nhận dạng hình dạng tay tĩnh (nắm, xoè), còn cú đấm là chuyển động. Nhóm ghép hình dạng tay với chuyển động của landmark qua nhiều frame, dùng state machine cho từng tay, có ngưỡng chấp nhận và cooldown.
- **Kỹ thuật tối ưu dự kiến** (đo trước/sau từng kỹ thuật): chạy song song capture và inference, giảm độ phân giải, crop vùng tay, frame skipping + tracking, giả lập máy yếu. ONNX Runtime và quantization áp dụng khi tích hợp model close source.

## 4. Đã làm được

- Chốt ý tưởng game, luật chơi, tập cử chỉ và phân công (họp 26/10/2026).
- Chạy thử **MediaPipe Gesture Recognizer** trên CPU, chỉ tính thời gian model:

  | Cấu hình | Trung bình | p95 |
  |---|---|---|
  | Theo dõi 1 tay | ~9 ms | 12 ms |
  | Cho phép 2 tay | ~28 ms | 42 ms |

  Có sẵn 21 landmark mỗi tay và phân biệt trái/phải. Chưa đủ dữ liệu để kết luận về độ chính xác.
- Dựng **khung code** cho toàn bộ pipeline: capture, interface recognizer (MediaPipe + phát lại dữ liệu ghi sẵn), khung state machine, đo thời gian, gửi UDP, nhận UDP bên Unity. Có công cụ test webcam và đánh giá trên tập ảnh. Phần nhận cú đánh và gameplay **chưa cài đặt**.

## 5. Phân công

| Thành viên | Phụ trách |
|---|---|
| Thái | Pipeline thời gian thực (capture, inference, tối ưu, benchmark), cầu nối UDP, nền AR trong Unity |
| Duy | Nhận diện cú đánh (tay trái/phải, state machine, ngưỡng), bộ dữ liệu + đo độ chính xác, tay 3D và hình bay trong Unity |
| Thảo | Gameplay (máy bắn, trúng/trượt, điểm, combo, level, bảng xếp hạng), khung cảnh, UI, âm thanh |

## 6. Kế hoạch

| Giai đoạn | Thời gian | Kết quả |
|---|---|---|
| 1. Nền móng | 27/10 – 8/11 | Nhận diện 2 tay, gửi dữ liệu sang Unity; nhận được đấm thẳng; khối bay trong Unity (đánh bằng bàn phím) |
| 2. Ghép bản thô | 9/11 – 22/11 | **Mốc 22/11:** đấm tay thật trước webcam → khối trong Unity vỡ, có nền AR |
| 3. Tối ưu + hoàn thiện | 23/11 – 20/12 | Bảng benchmark trước/sau tối ưu; đủ 3 cử chỉ + bảng độ chính xác; Level 1 hoàn chỉnh |
| 4. Hoàn thiện + báo cáo | 21/12 – 1/2027 | Tích hợp model close source, so sánh với MediaPipe; thêm level; demo và báo cáo cuối kỳ |

