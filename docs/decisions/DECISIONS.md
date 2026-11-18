# Decisions

Sổ các quyết định đã thống nhất giữa nhiều người: họp nhóm, báo cáo trên lớp, góp ý của giảng viên (trực tiếp hoặc online). Mỗi quyết định một dòng, mới nhất ở trên. Chi tiết nằm trong file biên bản cùng thư mục, đặt tên `YYYY-MM-DD_<nguồn>_<chủ-đề>.md` theo mẫu [`_template.md`](_template.md).

Nguồn: `hop-nhom` · `hop-gv` · `bao-cao-lop` · `gop-y-online`

Khi quyết định ở đây mâu thuẫn với `docs/planning/`, quyết định ở đây được ưu tiên.

| Ngày | Quyết định | Nguồn | Biên bản |
| --- | --- | --- | --- |
| 2026-11-16 | Kế hoạch 8 sprint, mỗi sprint 1 tuần (16/11/2026 – 10/1/2027), demo giữa tháng 1/2027; thay bảng "Mốc" trong `PHAN_CONG.vi.md` | `<bổ sung>` | [sprints/README.md](../sprints/README.md) |
| 2026-11-16 | Tạm bỏ việc tích hợp model close source (kéo theo ONNX / quantization); nếu có lại thì xếp sau mốc M3 (27/12) | `<bổ sung>` | — |
| 2026-11-16 | Giữ kiến trúc Python (nhận diện) + Unity (game, AR) qua UDP. Project Unity tạo lại bằng Unity Editor ở gốc repo (commit `0587ebe`); code Python đưa lại vào `python/` từ commit `44a3e6b` | `<bổ sung>` | — |
| 2026-10-26 | Phân công 3 người theo lát dọc: Thái – pipeline + AR, Duy – cử chỉ tay, Thảo – gameplay | `hop-nhom` | [biên bản](2026-10-26_hop-nhom_doi-game-move-fast.md) |
| 2026-10-26 | Âm thanh chỉ là nhạc nền, không theo nhịp. Hình ảnh sống động, màu hài hoà | `hop-nhom` | [biên bản](2026-10-26_hop-nhom_doi-game-move-fast.md) |
| 2026-10-26 | Game có level (Level 1 trước), điểm, combo, top score, bảng xếp hạng, mở khoá level | `hop-nhom` | [biên bản](2026-10-26_hop-nhom_doi-game-move-fast.md) |
| 2026-10-26 | Nhận diện tay trái/phải, bên nào đánh bên đó. Cử chỉ: đấm thẳng, đấm thủ, xoè tay (đấm móc tuỳ chọn). Có ngưỡng chấp nhận cử chỉ | `hop-nhom` | [biên bản](2026-10-26_hop-nhom_doi-game-move-fast.md) |
| 2026-10-26 | Bỏ puzzle xếp khối, chốt game đấm khối kiểu Move Fast | `hop-nhom` | [biên bản](2026-10-26_hop-nhom_doi-game-move-fast.md) |
