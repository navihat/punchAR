# Unity workflow

## Unity quản lý file thế nào

- Unity chỉ import những gì trong `Assets/`. Mỗi file/thư mục ở đó có một file `.meta` chứa **GUID**.
- Scene và prefab tham chiếu tới script, material, texture **bằng GUID**, không bằng tên file.
- `Library/` là bộ nhớ đệm import, tự tạo lại được, không commit.
- Project đặt Asset Serialization = **Force Text** (đã kiểm tra trong `ProjectSettings/EditorSettings.asset`), nên scene/prefab là YAML, đọc và diff được.

## Quy tắc

| Việc | Làm thế nào |
| --- | --- |
| Đổi tên / di chuyển file trong `Assets/` | Làm trong Unity Editor; nếu làm ngoài thì phải di chuyển cả `.meta` |
| Xoá file | Xoá cả `.meta` |
| Tạo thư mục mới | Chỉ tạo khi có file đầu tiên bỏ vào (git không lưu thư mục rỗng nhưng lưu `.meta` của nó) |
| Tạo file ngoài Unity (VS Code, agent) | Mở Unity một lần để sinh `.meta`, rồi commit file + `.meta` cùng lúc |
| Sửa scene / prefab | Chỉ trong Unity Editor, không sửa tay file YAML |
| Đang ở Play mode | Mọi thay đổi trong Inspector sẽ mất khi dừng Play |
| Tài liệu (`.md`, `.docx`, `.pdf`) | Để ngoài `Assets/` |

## Agent được làm gì

| File | Đọc | Sửa |
| --- | --- | --- |
| `.cs`, `.asmdef`, `.json`, `.md` | ✓ | ✓ |
| `.unity`, `.prefab`, `.asset`, `.meta` | ✓ (tìm tham chiếu, xem giá trị đã lưu) | ✗ |
| `ProjectSettings/`, `Packages/packages-lock.json` | ✓ | ✗ |
| `Library/`, `Temp/`, `Logs/`, `UserSettings/` | — | ✗ |

## Mẹo đọc YAML

Tìm scene/prefab đang dùng `UdpReceiver.cs`:

```bash
guid=$(grep -m1 '^guid:' Assets/Scripts/UdpReceiver.cs.meta | cut -d' ' -f2)
grep -rl "$guid" Assets --include='*.unity' --include='*.prefab'
```
