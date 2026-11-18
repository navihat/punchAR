# AGENTS.md — punchAR: game đấm khối AR điều khiển bằng cử chỉ tay

Game phản xạ trên PC + webcam (lối chơi tham khảo *Move Fast*): máy bắn phóng hình bay về phía người chơi, hình bay bên nào thì dùng tay bên đó, làm đúng cử chỉ (đấm thẳng, đấm thủ, xoè tay) để phá hình. Đối tượng 3D vẽ chồng lên hình webcam (AR). Học phần ED4140 — Đồ án VR/AR, đề tài "Các kỹ thuật hỗ trợ mô hình AI đáp ứng thời gian thực trong xử lý chuỗi hình ảnh". Nhóm 3 người, demo giữa tháng 1/2027.

**Trọng tâm chấm điểm là kỹ thuật thời gian thực** (độ trễ, FPS, độ chính xác và độ ổn định nhận diện). Game là nơi kiểm chứng các kỹ thuật này.

## Stack

- **Python** (nhận diện): OpenCV, MediaPipe Gesture Recognizer (CPU), numpy, pytest
- **Unity 6000.6.4f1**, URP, C#, Input System (game, AR)
- Python gửi JSON qua **UDP** (`127.0.0.1:5005`) sang Unity
- Asset Serialization = Force Text: `.unity`, `.prefab`, `.asset`, `.meta` là YAML đọc được
- Máy đo chuẩn: laptop i5-12450H, 8 GB RAM, inference chạy trên CPU

## Luồng chạy

```
Webcam → [1] Capture → [2] Recognizer → [3] Decision Logic → (UDP) → [4] Unity: game + AR
          luồng riêng     thay được        ngưỡng, thời gian
                     [5] Metrics: timestamp ở mọi khâu để đo độ trễ
```

## Cấu trúc

```
python/            pipeline nhận diện — CHƯA CÓ trên main, đang khôi phục từ commit 44a3e6b (Sprint 1)
  punchar/         capture/, recognizer/, decision/, transport/, metrics/
  config/          default.toml — mọi ngưỡng và tham số, thời gian tính bằng ms
  tools/           live_test.py, benchmark.py, eval_dataset.py
  tests/
models/            gesture_recognizer.task (MediaPipe)
Assets/_Project/   code và asset Unity của nhóm, mỗi thư mục con một người sở hữu (Network/, AR/, Hands/, Targets/, Gameplay/, UI/, Audio/)
Assets/Scenes/     Main.unity (một người giữ) + Sandbox_<Tên>.unity — mỗi người một scene riêng
docs/              tài liệu, xem docs/README.md
```

| Phần | Phụ trách | Nội dung |
| --- | --- | --- |
| Capture, recognizer, metrics, UDP, nền AR | Thái | `python/punchar/capture/`, `recognizer/`, `transport/`, `metrics/`, `tools/benchmark.py`; `UdpReceiver.cs`, `Messages.cs`, nền webcam trong Unity |
| Cử chỉ tay | Duy | `python/punchar/decision/`, bộ dữ liệu, độ chính xác; tay 3D, hình bay, effect trong Unity |
| Gameplay | Thảo | máy bắn, trúng/trượt, điểm, combo, level, UI, âm thanh trong Unity |

## Quy tắc bắt buộc

1. **Được đọc, không được sửa** `.unity`, `.prefab`, `.meta`, `ProjectSettings/*`, `Packages/packages-lock.json`. Cần thay đổi scene/prefab thì mô tả các bước để người làm trong Unity Editor.
2. **File mới** (`.cs`...) được tạo; Unity tự sinh `.meta` khi mở Editor; commit file cùng `.meta` của nó. **Di chuyển / đổi tên / xoá** file trong `Assets/` phải xử lý cả file `.meta` đi kèm (dùng `git mv` cho cả hai), nếu không scene sẽ báo "Missing Script".
3. Không tạo thư mục rỗng trong `Assets/`.
4. Không đụng `Library/`, `Temp/`, `Logs/`, `UserSettings/` (Unity tự sinh, không commit).
5. **Định dạng tin UDP là hợp đồng giữa Python và Unity** (`transport/udp_sender.py` ↔ `Assets/_Project/Network/Messages.cs`). Không đổi một phía; đổi thì sửa cả hai và ghi vào `docs/team/PHAN_CONG.vi.md`, mục "Chỗ giao nhau".
6. Game chỉ nhận event qua UDP, không gọi model trực tiếp. Recognizer đi qua interface trong `recognizer/base.py` để thay model mà không sửa game.
7. Mọi luật theo thời gian (giữ, cooldown, ngưỡng) nằm ở Decision Logic, tham số đặt trong `config/default.toml`, tính bằng **ms**, không theo số frame.
8. Lật gương ảnh và quy đổi tay trái/phải theo góc nhìn người chơi chỉ làm **ở một chỗ** trong pipeline.
9. Mỗi kỹ thuật tối ưu phải đo trước/sau bằng `tools/benchmark.py` trên video quay sẵn; báo p50/p95/p99, không chỉ trung bình.

## Đọc file Unity để hỗ trợ dev

- Tìm GameObject đang dùng một script: lấy `guid` trong `X.cs.meta`, rồi `grep` guid đó trong `Assets/**/*.unity` và `*.prefab`.
- Xem giá trị field `[SerializeField]` đã lưu: tìm block `MonoBehaviour` có `m_Script: {guid: ...}` trong scene/prefab.
- Tham chiếu dạng `{fileID: 0}` ở field bắt buộc thường là chưa gán trong Inspector.

## Lệnh

Khi `python/` đã có trên `main`, chạy từ thư mục `python/`:

```bash
pip install -r requirements.txt
python -m punchar.main          # toàn bộ pipeline, gửi UDP sang Unity; Ctrl+C in bảng thời gian
python -m pytest                # unit test
```

## Tài liệu chi tiết

- `docs/README.md` — mục lục tài liệu
- `docs/planning/PROJECT_OVERVIEW.vi.md` — bối cảnh, kiến trúc, interface `FrameResult`, logic quyết định, chỉ số cần đo
- `docs/team/PHAN_CONG.vi.md` — phân công và chỗ giao nhau giữa các phần
- `docs/team/code-structure.md` — đặt code vào thư mục nào, thư mục nào của ai, file dùng chung. **Code mới phải đặt đúng thư mục ở đây**
- `docs/team/gitflow.md` — nhánh, commit, PR, xử lý conflict
- `docs/team/unity-workflow.md` — cách làm việc với Unity (GUID, scene, prefab)
- `docs/sprints/` — kế hoạch sprint; sprint đang chạy ghi ở `docs/README.md`
- `docs/decisions/DECISIONS.md` — quyết định đã chốt; ưu tiên hơn tài liệu planning khi mâu thuẫn
