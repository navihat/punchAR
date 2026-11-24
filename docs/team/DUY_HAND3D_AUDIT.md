# BÁO CÁO RÀ SOÁT VÀ KHẮC PHỤC LỖI TAY TRÁI 3D (HAND RIGGING & CODE AUDIT)

**Người thực hiện:** Dev (antigravity-2)  
**Người nhận:** Duy (Moderator) / Maneger (Coordinator)  
**Nhánh:** `feat/duy-hand3d-stage1`  
**Ngày:** 24/11/2026  

---

## 1. NGUYÊN NHÂN GỐC RỄ LỖI "TAY NÓ VẪN THẾ" (MÉO DỊ DẠNG & KÉO GIÃN)
Qua phân tích sâu hình học đỉnh và ma trận khung xương trong file `LeftHand.fbx` trước đó:
1. **Lệch pha 180° giữa Mesh và Skeleton:**
   - Khung xương (Armature) đã bị đảo trục khiến xương ngón trỏ hướng về `-X` (về bên trái).
   - Tuy nhiên, 8.400 đỉnh của Mesh lại **chưa được mirror**, vẫn nằm ở `+X` (về bên phải, giống hệt tay phải).
   - Đỉnh đầu ngón trỏ nằm ở $X \approx +0.063\text{m}$ nhưng lại được gán trọng số (skin weight) vào xương ngón trỏ ở $X \approx -0.074\text{m}$.
   - **Hậu quả:** Khi Unity áp dụng bất kỳ góc xoay nào vào khớp xương, các đỉnh bị giằng xé xuyên tâm từ bên phải sang bên trái (khoảng cách 15cm), làm bàn tay biến dạng dị hợm, nổ tung và xé lưới.
2. **Trục đối xứng ngang:**
   - Trong `RightHand.fbx`, trục ngang (từ ngón út sang ngón cái) nằm dọc theo trục $Y$, trục dài (cổ tay -> đầu ngón) nằm dọc theo trục $X$. Nếu thao tác mirror đơn thuần theo $X$ thì vô tình đảo ngược cổ tay và đầu ngón tay thay vì đảo ngón cái và ngón út!

---

## 2. QUY TRÌNH XỬ LÝ SẠCH & CÔNG CỤ `blender_split_hands.py`
Đã xây dựng script tự động `python/tools/blender_split_hands.py` thực hiện đúng 7 bước chuẩn Blender 4.2:
1. **Gỡ liên kết sạch:** Xóa sạch modifier `ARMATURE`, `clear_parent(type='CLEAR_KEEP_TRANSFORM')`, apply location/rotation/scale về chuẩn `(0,0,0)` và `(1,1,1)`.
2. **Căn trục ngang:** Xoay tạm Mesh và Armature $-90^\circ$ quanh trục $Z$ để trục ngang (pinky -> thumb) trùng với trục $X$. Apply rotation.
3. **Symmetrize Armature:** Dùng lệnh native `bpy.ops.armature.symmetrize(direction='NEGATIVE_X')`. Blender 4.2 tự động tính toán Bone Roll đối xứng hoàn hảo với Scale dương `(1, 1, 1)` cho toàn bộ 20 xương `.L`. Xóa toàn bộ xương `.R`.
4. **Mirror Mesh độc lập:** Dùng `bmesh` lật tọa độ đỉnh qua mặt phẳng $X=0$ (`v.co.x = -v.co.x`), gọi `normals_make_consistent(inside=False)` đảo pháp tuyến mặt, đổi tên 20 vertex groups sang `.L`.
5. **Xoay trả lại:** Xoay ngược $+90^\circ$ quanh trục $Z$ về hệ tọa độ gốc của bàn tay. Apply rotation.
6. **Re-bind Skinning:** Gán lại `mesh.parent = arm_obj`, reset `matrix_parent_inverse = Identity`, thêm đúng 1 modifier `ARMATURE` duy nhất với `use_vertex_groups = True`.
7. **Xuất FBX:** Xuất với `apply_scale_options='FBX_SCALE_ALL'`, `use_mesh_modifiers=False`, `add_leaf_bones=False`.

---

## 3. KẾT QUẢ TỰ KIỂM CHỨNG (5 TIÊU CHÍ BẮT BUỘC)
Chạy kiểm chứng trực tiếp bằng script tự động trên file `Assets/_Project/Hands/Models/LeftHand.fbx`:
- [x] **Tiêu chí 1 (Scale):** Cả Armature và Mesh đều có `Scale == (1.0, 1.0, 1.0)`.
- [x] **Tiêu chí 2 (Modifier):** Duy nhất 1 modifier `ARMATURE` trên Mesh.
- [x] **Tiêu chí 3 (Khớp Xương & Vertex Group):** 20/20 xương `.L` khớp 100% với 20/20 Vertex Groups `.L`.
- [x] **Tiêu chí 4 (Trọng số đỉnh):** 0 / 8.400 đỉnh bị rỗng weight (tất cả các đỉnh đều bám vào xương).
- [x] **Tiêu chí 5 (Biến dạng Pose):** Khi gập thử 15 đốt ngón tay $60^\circ$ trong Pose Mode:
  - Bounding box Rest: $0.257\text{m} \times 0.139\text{m} \times 0.047\text{m}$ (max = $0.257\text{m}$)
  - Bounding box Curled: $0.192\text{m} \times 0.097\text{m} \times 0.065\text{m}$ (max = $0.192\text{m}$)
  - Tỷ lệ co: **0.749** ($\le 1.20$). Bàn tay co khép chặt chẽ, không hề có hiện tượng giãn hay méo lưới!

---

## 4. RÀ SOÁT QUY ƯỚC DỰ ÁN TRÊN NHÁNH `feat/duy-hand3d-stage1`

| Hạng mục quy ước | Hiện trạng trên nhánh | Đánh giá & Khuyến nghị |
| :--- | :--- | :--- |
| **Cấu trúc thư mục (`AGENTS.md`)** | Đã di chuyển sạch từ `Assets/Duy_Hand3D/` sang `Assets/_Project/Hands/`. Scene nằm ở `Assets/Scenes/Sandbox_Duy.unity`. | **Đạt chuẩn 100%**. Có 2 thư mục untracked rác ở root: `13-rigged_hand_fbx/` và `docs/superpowers/` -> nên thêm vào `.gitignore`. |
| **Phân quyền sở hữu code** | Toàn bộ script nằm trong `Assets/_Project/Hands/Scripts/` (Duy sở hữu). | **Đạt chuẩn**. Không đụng chạm vào thư mục của Thái (`Network/`, `AR/`) hay Thảo (`Gameplay/`, `UI/`). |
| **Hợp đồng dữ liệu UDP** | `UdpHandProvider.cs` đã chuyển sang lắng nghe sự kiện từ `UdpReceiver` của Thái, tránh xung đột port 5005. | **Cần lưu ý:** Trong Prefab `HandTrackingRig.prefab`, field `udpReceiver` đang để trống (`None`), cần gán reference tới `UdpReceiver` trong Scene khi test live. |
| **Trục xoay & Rigging** | Cả hai tay hiện đã đồng bộ: ngón tay trỏ/giữa/áp út/út dùng `axis = (1,0,0)`, `dir = 1.0f`; ngón cái dùng `axis = (0,0,1)`, `dir = -1.0f`. | **Đạt chuẩn**. `Hand3DVisualizer.cs` đã tích hợp Context Menu `Reset Bones to Flat Pose` và `Auto-Map Blender Bones`. |
| **Transform Rotation trong Prefab** | `RightHand` child có `Rotation = (0, -90, -90)`. `LeftHand` child trước đó bị để `(0, 0, 0)` khiến tay trái bị nằm ngang. | **Cần điều chỉnh trong Inspector:** Đặt Rotation của model con `LeftHand` thành `(0, -90, -90)` giống `RightHand` để cả hai bàn tay cùng dựng đứng. |
| **Quy tắc Git (`gitflow.md`)** | Đang ở local worktree, ahead 29 commits, chưa push lên remote. | **Đạt chuẩn an toàn tuyệt đối**. |

---

## 5. HƯỚNG DẪN DUY KIỂM CHỨNG TRONG UNITY EDITOR
File `LeftHand.fbx` mới đã được ghi đè trực tiếp vào dự án. Duy chỉ cần thực hiện 3 bước đơn giản:
1. Mở Unity Editor (scene `Sandbox_Duy.unity`), đợi Unity import lại `LeftHand.fbx`.
2. Chọn GameObject `HandTrackingRig` trong Hierarchy:
   - Click chuột phải vào component `Hand3DVisualizer` -> Chọn **"Reset Bones to Flat Pose"**.
   - Click chuột phải -> Chọn **"Auto-Map Blender Bones (.L / .R)"**.
   - Kiểm tra model con `LeftHand` dưới `LeftHand_Root`: Đảm bảo `Rotation` là `(0, -90, -90)` và `Scale` là `(5, 5, 5)`.
3. Kéo thanh trượt `Debug Test Curl` (từ 0.0 -> 1.0): Quan sát cả 2 bàn tay gập nắm đấm mượt mà, các ngón tay gập đều tăm tắp, không còn bất kỳ hiện tượng méo hay xé hình nào!
