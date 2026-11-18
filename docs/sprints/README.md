# KẾ HOẠCH SPRINT — Game đấm khối AR

> Lập ngày 16/11/2026. Thay cho bảng "Mốc" trong [`PHAN_CONG.vi.md`](../team/PHAN_CONG.vi.md) (bảng đó trễ so với thực tế).
> Phân vai giữ nguyên theo [`PHAN_CONG.vi.md`](../team/PHAN_CONG.vi.md): Thái = pipeline + AR, Duy = cử chỉ tay, Thảo = gameplay.

**Điểm xuất phát (16/11):** repo chỉ có project Unity mẫu, chưa phần nào chạy được. Khung Python cũ còn trong lịch sử git (commit `44a3e6b`).

**Quy ước**
- Sprint dài 1 tuần, thứ Hai → Chủ nhật. Còn 8 sprint đến demo giữa tháng 1/2027.
- Chủ nhật cuối mỗi sprint: cả 3 họp ghép thử trên nhánh `main`, đối chiếu cột "Xong khi".
- Việc không xong thì chuyển sang sprint sau và cắt bớt việc "nếu kịp", không kéo dài sprint.
- Kiến trúc: Python (nhận diện) + Unity (game, AR), trao đổi qua UDP.
- **Ngoài phạm vi lúc này:** model close source (kéo theo ONNX / quantization). Nếu có lại thì xếp vào sau mốc M3.
- Mỗi sprint một file `sprint-NN.md`. Chỉ sprint đang chạy được chi tiết hoá theo ngày.

**Mốc lớn**

| Mốc | Ngày | Nội dung |
|---|---|---|
| M1 | 29/11 | Đấm tay thật trước webcam → khối trong Unity vỡ |
| M2 | 13/12 | Chơi trọn Level 1 bằng tay thật, đủ 3 cử chỉ, trên nền AR |
| M3 | 27/12 | Chốt tính năng, sau mốc này chỉ sửa lỗi |
| M4 | 10/1 | Sẵn sàng demo: bản chạy, báo cáo, slide |

## Lộ trình

| Sprint | Ngày | Mục tiêu | Mốc | File |
|---|---|---|---|---|
| 1 | 16/11 – 22/11 | Nền móng: pipeline gửi vị trí tay sang Unity, nhận đấm thẳng, khối bay đánh bằng bàn phím | | [sprint-01.md](sprint-01.md) |
| 2 | 23/11 – 29/11 | Ghép bản thô: tin `strike` từ webcam vào game | M1 | [sprint-02.md](sprint-02.md) |
| 3 | 30/11 – 6/12 | Nền AR, đủ 3 cử chỉ, lịch phóng theo level | | [sprint-03.md](sprint-03.md) |
| 4 | 7/12 – 13/12 | Level 1 chơi được, bộ dữ liệu, tối ưu đợt 1 | M2 | [sprint-04.md](sprint-04.md) |
| 5 | 14/12 – 20/12 | Tối ưu đợt 2, độ chính xác ≥ 90%, bảng xếp hạng | | [sprint-05.md](sprint-05.md) |
| 6 | 21/12 – 27/12 | Hoàn thiện tính năng: đo end-to-end, Level 2 | M3 | [sprint-06.md](sprint-06.md) |
| 7 | 28/12 – 3/1 | Sửa lỗi, viết báo cáo, video demo dự phòng | | [sprint-07.md](sprint-07.md) |
| 8 | 4/1 – 10/1 | Chuẩn bị demo: máy demo, slide, tập demo | M4 | [sprint-08.md](sprint-08.md) |

## Nếu bị trễ thì cắt theo thứ tự này

1. Đấm móc
2. Level 2 và mở khoá level (giữ Level 1 + bảng xếp hạng)
3. Animation máy bắn, khung cảnh xung quanh
4. Tự giảm chất lượng khi máy quá tải (còn 3 kỹ thuật tối ưu)

Không cắt: M1, M2, bảng benchmark trước/sau, bảng độ chính xác. Đây là phần trả lời trực tiếp đề tài.
