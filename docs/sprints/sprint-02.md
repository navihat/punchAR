# Sprint 2 (23/11 – 29/11): Ghép bản thô → M1

> Lộ trình và quy ước chung: [README.md](README.md). Chi tiết theo ngày lập ở buổi họp CN 22/11.

| Ai | Việc | Xong khi |
|---|---|---|
| Thái | Nối module của Duy vào pipeline, gửi `STRIKE` qua UDP. Ghi timestamp ở từng khâu. Chốt cách đưa hình webcam sang Unity (Python đang giữ camera nên Unity không mở trực tiếp được) | Một lệnh chạy Python, Unity nhận được `STRIKE` kèm `t_ms` |
| Duy | State machine từng tay (`IDLE → WINDUP → STRIKE → COOLDOWN`), ngưỡng và cooldown để trong config. Tay 3D bản thô trong Unity (các khối cầu ở vị trí landmark) | Đấm 10 cú thì phát ra 10 `STRIKE`, không cú nào bị tính đôi |
| Thảo | Game nhận `STRIKE` thay cho bàn phím (giữ bàn phím làm dự phòng). Kiểm tra trúng/trượt theo tay + loại cú đánh. Điểm và combo cơ bản | Đấm đúng tay thì khối vỡ, cộng điểm; sai tay thì mất combo |

**M1 (29/11):** đấm tay thật trước webcam → khối trong Unity vỡ.

## Ghi chú review (24/11)

Review nhánh của Duy (`feat/duy-hand3d-stage1`, `fix/hands-left-rig`), chưa có PR:

- Hai nhánh cùng tách từ `c7e8a6f`, làm lại cùng một việc (rig tay 3D); merge với nhau conflict 7 file (`.unity`, 2 `.fbx`, `Hand3DVisualizer.cs`, audit doc, 2 tool Python). Từng nhánh merge vào `main` thì sạch.
- Chọn `fix/hands-left-rig` làm nhánh merge (mới hơn, sửa FBX tay trái, `mock_udp_streamer.py` được `simulate_hand_stream.py` thay). Duy xác nhận `stage1` không còn gì riêng rồi bỏ.
- `pytest`: 11 test pass trên `fix/hands-left-rig`.
- Cần kiểm trước khi merge: `.prefab`/`.unity` do Unity Editor sinh (không sửa tay); ngưỡng `state_machine.py` nằm hết trong `default.toml` tính bằng ms; lật gương handedness chỉ một chỗ; gán `udpReceiver` và Rotation `LeftHand` trong Unity.
- Chưa có số đo benchmark (p50/p95/p99) hay độ chính xác nhận diện cho phần của Duy.
