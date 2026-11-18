# Sprint 2 (23/11 – 29/11): Ghép bản thô → M1

> Lộ trình và quy ước chung: [README.md](README.md). Chi tiết theo ngày lập ở buổi họp CN 22/11.

| Ai | Việc | Xong khi |
|---|---|---|
| Thái | Nối module của Duy vào pipeline, gửi `STRIKE` qua UDP. Ghi timestamp ở từng khâu. Chốt cách đưa hình webcam sang Unity (Python đang giữ camera nên Unity không mở trực tiếp được) | Một lệnh chạy Python, Unity nhận được `STRIKE` kèm `t_ms` |
| Duy | State machine từng tay (`IDLE → WINDUP → STRIKE → COOLDOWN`), ngưỡng và cooldown để trong config. Tay 3D bản thô trong Unity (các khối cầu ở vị trí landmark) | Đấm 10 cú thì phát ra 10 `STRIKE`, không cú nào bị tính đôi |
| Thảo | Game nhận `STRIKE` thay cho bàn phím (giữ bàn phím làm dự phòng). Kiểm tra trúng/trượt theo tay + loại cú đánh. Điểm và combo cơ bản | Đấm đúng tay thì khối vỡ, cộng điểm; sai tay thì mất combo |

**M1 (29/11):** đấm tay thật trước webcam → khối trong Unity vỡ.
