# Git workflow: làm việc thế nào để không conflict

> Bản nháp 18/11/2026 — nhóm review và chốt ở buổi họp CN 22/11.

Nhóm 3 người, 8 tuần: dùng **GitHub Flow** — một nhánh `main` + nhánh ngắn cho từng việc. Thư mục nào của ai: [`code-structure.md`](code-structure.md).

## Nhịp hằng ngày

1. **Trước khi bắt đầu:** cập nhật `main` và nhánh của mình.
   ```bash
   git switch main && git pull
   git switch <nhánh-của-mình> && git merge main
   ```
2. **Trong khi làm:** commit nhỏ, mỗi commit một việc.
3. **Khi xong một bước** (theo cột "Xong khi" trong file sprint): push và mở PR ngay, không giữ nhánh quá **2 ngày**. Nhánh càng sống lâu càng dễ conflict.
4. **Tắt Unity Editor trước khi `pull` / `merge` / `switch`** để Unity không ghi đè file trong lúc git đang đổi.

## Nhánh

- `main` luôn chạy được: mở được trong Unity không lỗi, `python -m punchar.main` chạy được. Không push thẳng lên `main`.
- Nhánh việc: `<loại>/<phần>-<mô-tả>`, ví dụ `feat/decision-straight-punch`, `feat/gameplay-spawner`, `fix/network-handedness`.
- Loại: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`.
- Phần: tên thư mục trong [`code-structure.md`](code-structure.md) (`capture`, `decision`, `network`, `hands`, `gameplay`, `ui`...).

## Commit

Dạng Conventional Commits, tiếng Anh: `feat(decision): detect straight punch from hand size growth`.

## Pull Request

1. Một PR cho một việc trong file sprint; ghi mã việc hoặc tên việc trong mô tả.
2. Cần 1 người duyệt. PR sửa file của người khác thì người sở hữu file đó duyệt.
3. PR đổi hợp đồng dữ liệu (`udp_sender.py` ↔ `Messages.cs`) cần cả 3 người đồng ý.
4. PR có thay đổi scene/prefab: ghi rõ đã sửa object nào.
5. Squash merge, xoá nhánh sau khi merge.

## Unity

- Luôn commit file `.meta` cùng file gốc. Chi tiết: [`unity-workflow.md`](unity-workflow.md).
- Chỉ lưu scene của mình (`Sandbox_<Tên>`). Unity hay tự đánh dấu scene đã mở là "có thay đổi"; nếu `git status` hiện scene của người khác bị sửa thì bỏ thay đổi đó (`git restore <file>`), không commit.
- Merge scene/prefab bằng UnityYAMLMerge — thêm vào `.git/config` của máy mình (đổi đường dẫn nếu cài Unity chỗ khác):

```ini
[merge "unityyamlmerge"]
    name = Unity SmartMerge
    driver = ~/Unity/Hub/Editor/6000.6.4f1/Editor/Data/Tools/UnityYAMLMerge merge -p %O %B %A %A
    recursive = binary
```

## Khi gặp conflict

1. Conflict ở file **của mình**: tự sửa.
2. Conflict ở file **của người khác** hoặc file dùng chung: gọi người sở hữu, sửa cùng nhau.
3. Conflict ở **scene / prefab** mà UnityYAMLMerge không gộp được: không sửa tay YAML. Giữ một bản (`git checkout --ours` hoặc `--theirs`), mở Unity làm lại phần thay đổi kia.

## Git LFS

Ảnh, PDF, DOCX, DLL, model 3D, video đi qua LFS (xem `.gitattributes`). Chạy `git lfs install` một lần trước commit đầu tiên. Video quay bộ dữ liệu và video demo để trên Google Drive, trong repo chỉ để link.
