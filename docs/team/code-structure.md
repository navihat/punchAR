# Cấu trúc code: đặt code vào đâu, thư mục nào của ai

> Bản nháp 18/11/2026 — nhóm review và chốt ở buổi họp CN 22/11.

**Nguyên tắc:** mỗi thư mục có **một người sở hữu**. Chỉ người đó sửa file trong thư mục của mình. Cần sửa thư mục của người khác thì báo người đó, hoặc mở PR và để người đó review. Hai người không cùng sửa một file thì gần như không bao giờ conflict.

Cách các phần nối với nhau: xem 5 điểm nối ở mục "Chỗ giao nhau" của [`PHAN_CONG.vi.md`](PHAN_CONG.vi.md) và [`PROJECT_OVERVIEW.vi.md`](../planning/PROJECT_OVERVIEW.vi.md) mục 5.

## Python (`python/`)

```
python/
├── punchar/
│   ├── capture/        Thái   đọc webcam, luồng riêng, lật gương
│   ├── recognizer/     Thái   interface Recognizer + FrameResult, adapter MediaPipe, replay
│   ├── decision/       Duy    state machine từng tay, sinh StrikeEvent
│   ├── transport/      Thái   gửi JSON qua UDP
│   ├── metrics/        Thái   đo thời gian từng khâu, báo cáo
│   └── main.py         Thái   vòng lặp chính, nối các khâu
├── config/default.toml chung  xem bảng "File dùng chung" bên dưới
├── tools/
│   ├── benchmark.py    Thái
│   ├── live_test.py    Duy    (và punch_debug.py nếu thêm)
│   └── eval_dataset.py Duy
├── tests/              test_<module>.py — người sở hữu module viết test của module đó
└── requirements.txt    chung
models/                 Thái   file model (gesture_recognizer.task)
```

## Unity (`Assets/`)

Code và asset của nhóm để trong `Assets/_Project/`, chia theo người sở hữu. Không đặt file của nhóm ở thư mục gốc `Assets/`.

```
Assets/
├── _Project/
│   ├── Network/        Thái   UdpReceiver.cs, Messages.cs
│   ├── AR/             Thái   nền webcam, căn khớp camera
│   ├── Hands/          Duy    tay 3D, chế độ debug (khung xương, nhãn cử chỉ)
│   ├── Targets/        Duy    hình bay tới: prefab, material, effect vỡ/trượt
│   ├── Gameplay/       Thảo   máy bắn, lịch phóng, trúng/trượt, điểm, combo, level, phím giả lập (GameManager.cs)
│   ├── UI/             Thảo   bảng điểm, menu, bảng xếp hạng
│   └── Audio/          Thảo   nhạc nền, âm thanh trúng/trượt
└── Scenes/
    ├── Main.unity             cảnh chơi chính — chỉ một người sửa (đề xuất: Thảo)
    ├── Sandbox_Thai.unity     Thái
    ├── Sandbox_Duy.unity      Duy
    └── Sandbox_Thao.unity     Thảo
```

- Mỗi thư mục con có thể chia tiếp `Scripts/`, `Prefabs/`, `Materials/` khi nhiều file.
- **Scene:** mỗi người thử nghiệm trong scene `Sandbox_<Tên>` của mình, không mở rồi lưu scene của người khác.
- **Đưa phần của mình vào `Main.unity`:** làm thành **prefab** trong thư mục của mình, rồi nhờ người giữ `Main.unity` kéo vào. Sửa prefab sau đó không đụng tới scene.
- Hình bay: Duy sở hữu prefab (hình dáng, màu, effect); Thảo chỉ sinh ra và điều khiển prefab đó từ `Gameplay/`.

## File dùng chung (dễ conflict nhất)

| File | Ai sửa | Quy tắc |
|---|---|---|
| `python/transport/udp_sender.py` ↔ `Assets/_Project/Network/Messages.cs` | Thái | Hợp đồng dữ liệu giữa Python và Unity. Đổi thì sửa cả hai cùng một PR, báo cả nhóm, ghi vào `PHAN_CONG.vi.md` |
| `python/config/default.toml` | Mỗi người một mục | `[capture]`, `[recognizer]`, `[transport]`: Thái · `[decision]`: Duy. Chỉ sửa mục của mình |
| `python/requirements.txt` | Ai cũng được | Thêm thư viện thì ghi trong mô tả PR, báo nhóm cài lại |
| `Assets/Scenes/Main.unity` | Người giữ scene | Xem mục Unity ở trên |
| `Packages/manifest.json`, `ProjectSettings/` | Báo nhóm trước | Cài package hoặc đổi setting trong Unity Editor sẽ sửa các file này; mỗi lần chỉ một người làm, commit riêng |
| `.gitignore`, `.gitattributes` | Báo nhóm trước | |
