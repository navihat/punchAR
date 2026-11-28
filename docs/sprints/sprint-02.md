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

## Review (điền ở buổi họp CN 29/11)

- **Số đo pipeline (Thái), 28/11:** `python -m punchar.main` với state machine của Duy và kênh ảnh webcam (`[video]` bật, JPEG 640×360 chất lượng 80), webcam trực tiếp 1280×720 MJPG, laptop i5-12450H (CPU). Đơn vị ms.

  | Khâu | n | mean | p50 | p95 | p99 |
  |---|---|---|---|---|---|
  | `recognize` | 2234 | 24.9 | 24.5 | 34.5 | 40.0 |
  | `decision` | 2234 | 0.0 | 0.0 | 0.1 | 0.1 |
  | `send` | 2234 | 0.2 | 0.2 | 0.3 | 0.4 |
  | `since_capture` | 2234 | 27.0 | 26.6 | 37.1 | 43.0 |
  | `video_encode` | 2234 | 1.2 | 1.1 | 1.7 | 2.0 |
  | `video_kb` (KB/gói) | 2234 | 25.7 | 25.8 | 26.8 | 27.1 |

  - `decision` giờ chạy logic thật của Duy (3 cử chỉ) nhưng vẫn < 0.1 ms: logic quyết định không tốn thời gian máy.
  - Ảnh JPEG ~26 KB/gói, vừa một gói UDP (tối đa 64 KB). Nén chạy ở luồng riêng (~1.1 ms p50), không nằm trong vòng lặp chính.
  - `recognize` p50 tăng 20.4 → 24.5 ms (+4.1 ms) so với lượt MJPG cuối Sprint 1. **Chưa rõ nguyên nhân:** có thể do luồng nén ảnh tranh CPU, do Unity chạy cùng lúc, hoặc do số tay trong hình khác nhau. Cần đo lại cùng điều kiện với `[video] enabled = false` để tách.
  - Chưa có số phía Unity (thời gian giải nén ảnh, `now − t` của ảnh nền): lượt này không lấy log `[WebcamBackground]`.
- **M1:** chưa thử được đấm vỡ khối bằng tay thật, vì tay 3D của Duy còn hiển thị sai. Bản sửa tay trái (nhánh `fix/hands-left-model-align`) đã chuyển cho Duy hoàn thiện.
- **Việc chuyển sang Sprint 3:**
  - Đo lại `recognize` khi tắt/bật `[video]`; lấy số giải nén phía Unity.
  - Thử M1 sau khi Duy sửa xong tay 3D.
