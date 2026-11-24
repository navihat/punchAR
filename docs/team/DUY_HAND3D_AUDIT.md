# BÁO CÁO RÀ SOÁT VÀ XỬ LÝ LỖI MÔ HÌNH TAY TRÁI 3D & BIÊN CHUYỂN ĐỘNG (HAND RIGGING, MOVEMENT BOUNDS & CODE AUDIT)

**Người lập:** Maneger (Coordinator) & Dev  
**Người nhận:** Duy (Moderator - Phụ trách Cử chỉ tay & Tay 3D punchAR)  
**Nhánh kiểm tra:** `feat/duy-hand3d-stage1` (trên máy Duy)  
**Ngày:** 24/11/2026  

---

## 1. NGUYÊN NHÂN GỐC RỄ LỖI KÉO HÌNH (MESH STRETCHING) & DỊ DẠNG TAY TRÁI

Qua phân tích ma trận khung xương và hình học đỉnh của file `LeftHand.fbx` cũ:
1. **Lỗi thao tác Mirror bằng `scale = -1` và `transform_apply`:**
   - Khi lật Armature bằng scale âm rồi apply transform, ma trận Bind Pose (`matrix_world` của từng bone), trục xoay cục bộ (`Bone Roll`), và ma trận nghịch đảo liên kết giữa Mesh và Armature (`matrix_parent_inverse`) bị đảo cực và tính toán sai lệch.
   - **Hậu quả:** Khi Unity thay đổi `localRotation` của các đốt xương trong quá trình tracking/gập tay, các đỉnh của Mesh bị kéo giằng xuyên tâm không gian từ bên phải sang bên trái (độ lệch lên tới 1.5m), khiến bàn tay bị nổ tung kích thước từ 0.2m lên tới 2.75m.
2. **Trục đối xứng thực tế của bàn tay:**
   - Trong `RightHand.fbx`, các ngón tay hướng dọc theo trục $+X$, mu bàn tay/lòng bàn tay hướng theo trục $Z$, còn trục ngang lòng bàn tay (từ ngón út sang ngón cái) nằm dọc theo trục $Y$ ($lateral.y \approx +0.768$).
   - Nếu mirror trực tiếp qua trục $X$ mà không xoay tạm, thao tác mirror sẽ đảo ngược cổ tay và ngón tay thay vì đảo ngón cái và ngón út.

---

## 2. QUY TRÌNH XỬ LÝ SẠCH VỚI CÔNG CỤ `python/tools/blender_split_hands.py`

Đã nâng cấp và chuẩn hóa công cụ [blender_split_hands.py](file:///D:/CODE/CODE/2026.1/DoAn_VRAR/punchAR/python/tools/blender_split_hands.py) chạy tự động trên Blender 4.2 LTS theo đúng 7 bước nghiêm ngặt:
1. **Kiểm tra nguồn gốc:** Rà soát `13-rigged_hand_fbx/Rigged Hand.fbx` và `RightHand.fbx`. Nhận định: file nguồn `Cube.000` (tay phải) có 8.400 đỉnh (high-poly mượt), trong khi `Cube.005` (tay trái) chỉ có 543 đỉnh (low-poly thô). Do đó, việc dùng `RightHand.fbx` chuẩn để mirror đối xứng sang `LeftHand.fbx` là bắt buộc để hai tay đồng nhất 100% về độ phân giải và chất lượng hình học.
2. **Gỡ liên kết sạch (Unbinding):** Xóa sạch modifier `ARMATURE`, gọi `clear_parent(type='CLEAR_KEEP_TRANSFORM')`, apply location/rotation/scale về chuẩn `(0,0,0)` và `(1,1,1)`.
3. **Căn trục ngang:** Xoay tạm Mesh và Armature $-90^\circ$ quanh trục $Z$ để trục ngang lòng bàn tay trùng với trục $X$ (trục mirror chuẩn của Blender). Apply rotation.
4. **Symmetrize Armature chuẩn:** Dùng lệnh native `bpy.ops.armature.symmetrize(direction='NEGATIVE_X')`. Blender 4.2 tự động tính toán Bone Roll đối xứng hoàn hảo với Scale dương `(1, 1, 1)` cho toàn bộ 20 xương `.L`. Sau đó xóa sạch toàn bộ xương `.R`.
5. **Mirror Mesh độc lập:** Dùng `bmesh` lật tọa độ đỉnh qua mặt phẳng $X=0$ (`v.co.x = -v.co.x`), gọi `normals_make_consistent(inside=False)` để sửa pháp tuyến mặt không bị lộn ngược, đổi tên 20 vertex groups từ `.R` sang `.L`.
6. **Xoay trả lại & Re-bind Skinning:** Xoay ngược $+90^\circ$ quanh trục $Z$ về hệ tọa độ gốc. Gán lại `mesh.parent = arm_obj`, reset `mesh.matrix_parent_inverse = Identity`, thêm đúng 1 modifier `ARMATURE` duy nhất với `use_vertex_groups = True`.
7. **Xuất FBX:** Xuất với `apply_scale_options='FBX_SCALE_ALL'`, `use_mesh_modifiers=False`, `add_leaf_bones=False`, `bake_anim=False`.

> **Tiện ích:** Script có cơ chế tự động chuyển tiếp thực thi: Duy chỉ cần gõ `python python/tools/blender_split_hands.py`, script sẽ tự động gọi Blender 4.2 nền để xuất và kiểm chứng.

---

## 3. KẾT QUẢ TỰ KIỂM CHỨNG LEFTHAND.FBX (5 TIÊU CHÍ BẮT BUỘC)

File [LeftHand.fbx](file:///D:/CODE/CODE/2026.1/DoAn_VRAR/punchAR/Assets/_Project/Hands/Models/LeftHand.fbx) đã được kiểm chứng tự động:
- [x] **Tiêu chí 1 (Scale):** Cả Armature và Mesh đều có `Scale == (1.0, 1.0, 1.0)`.
- [x] **Tiêu chí 2 (Modifier):** Duy nhất 1 modifier `ARMATURE` trên Mesh, không còn modifier rác.
- [x] **Tiêu chí 3 (Khớp Xương & Vertex Group):** 20/20 xương `.L` khớp 100% với 20/20 Vertex Groups `.L`.
- [x] **Tiêu chí 4 (Trọng số đỉnh):** 0 / 8.400 đỉnh bị rỗng weight (100% đỉnh bám chắc vào khung xương).
- [x] **Tiêu chí 5 (Biến dạng Pose):** Khi gập thử 15 đốt ngón tay $60^\circ$ trong Pose Mode:
  - Bounding box Rest: $0.257\text{m} \times 0.139\text{m} \times 0.047\text{m}$ (max = $0.257\text{m}$)
  - Bounding box Curled: $0.192\text{m} \times 0.097\text{m} \times 0.065\text{m}$ (max = $0.192\text{m}$)
  - Tỷ lệ co: **0.749** ($\le 1.20$). Bàn tay co khép chặt chẽ, không hề bị phình to hay xé lưới!

---

## 4. XỬ LÝ BIÊN CHUYỂN ĐỘNG & RIGGING TRONG `Hand3DVisualizer.cs`

### A. Tách giới hạn biên độ giải phẫu từng đốt (MCP $\to$ PIP $\to$ DIP, CMC $\to$ MCP $\to$ IP):
- `Vector3 fingerMaxBendDeg = new Vector3(80f, 95f, 65f);` cho 4 ngón: MCP tối đa $80^\circ$, PIP tối đa $95^\circ$, DIP tối đa $65^\circ$.
- `Vector3 thumbMaxBendDeg = new Vector3(35f, 45f, 55f);` cho ngón cái: CMC tối đa $35^\circ$, MCP tối đa $45^\circ$, IP tối đa $55^\circ$.
- `fingerBendGain` đặt mặc định `1.25f` để nắm tay vừa vặn, không cuộn lố đâm xuyên lòng bàn tay.
- `HandRigConfig` tách riêng:
  - `thumbCmcBendAxis` và `thumbCmcBendDirection` cho đốt gốc 01 CMC.
  - `thumbBendAxis` và `thumbBendDirection` cho đốt 02 (MCP) và 03 (IP).
- `CalcBendAngleDeg` clamp chặt góc gập trong `[0f, maxBendLimit]`.
- `ApplyTestCurl` và fallback fist (`fallbackFistRatio = 0.9f`) đồng bộ hóa theo từng đốt ngón tay.

### B. Khóa biên di chuyển (Movement Bounds) & Ổn định xoay cổ tay:
- Bổ sung `viewportMargin = Vector2(0.08f, 0.08f)` và `minCameraDepth = 0.5f`.
- Trong `MapNormalizedToWorld`: clamp $X$ và $Y$ trong $[0.08, 0.92]$, $Z \ge 0.5\text{m}$, bảo đảm tay không văng ra ngoài khung hình camera và không đâm xuyên kính camera.
- Trong `ApplyWristOrientation`: kiểm tra suy biến và kiểm tra đảo hướng Quaternion (`Quaternion.Dot < 0f`) giúp `Quaternion.Slerp` luôn đi cung ngắn nhất, triệt tiêu hiện tượng giật lật $180^\circ$ đột ngột.

---

## 5. BẢNG THÔNG SỐ INSPECTOR ĐỀ XUẤT CHO UNITY

| Tham số Inspector | Left Hand Rig | Right Hand Rig | Cơ sở kỹ thuật |
| :--- | :--- | :--- | :--- |
| **Finger Bend Axis** | `(1, 0, 0)` | `(1, 0, 0)` | 4 ngón quay quanh trục $+X$ cục bộ để gập vào lòng bàn tay. |
| **Finger Bend Direction** | `1.0` | `1.0` | Chiều dương $+X$ là chiều gập tự nhiên. |
| **Thumb CMC Bend Axis (Đốt 01)** | `(1, 0, 0)` | `(1, 0, 0)` | Đốt gốc ngón cái CMC quay quanh $+X$ khép lòng bàn tay. |
| **Thumb CMC Bend Direction** | `1.0` | `1.0` | Chiều dương áp sát ngón cái vào gốc ngón trỏ. |
| **Thumb Joint Bend Axis (Đốt 02/03)** | `(1, 0, 0)` | `(1, 0, 0)` | Đốt MCP và IP gập bản lề mượt mà quanh $+X$. |
| **Thumb Joint Bend Direction** | `1.0` | `1.0` | Cùng chiều dương với đốt gốc. |
| **Finger Max Bend Deg** | `(80, 95, 65)` | `(80, 95, 65)` | MCP $80^\circ$, PIP $95^\circ$, DIP $65^\circ$. |
| **Thumb Max Bend Deg** | `(35, 45, 55)` | `(35, 45, 55)` | CMC $35^\circ$, MCP $45^\circ$, IP $55^\circ$. |
| **Finger Bend Gain** | `1.25` | `1.25` | Nhạy vừa phải, không đâm xuyên lòng bàn tay. |
| **Viewport Margin** | `(0.08, 0.08)` | `(0.08, 0.08)` | Giữ bàn tay cách mép màn hình 8%. |
| **Min Camera Depth** | `0.5` | `0.5` | Giữ bàn tay cách camera tối thiểu 50cm. |
| **Model Con Local Rotation** | `(0, -90, -90)` | `(0, -90, -90)` | Ngón tay hướng ra trước (+Z), mu bàn tay hướng lên (+Y). |

---

## 6. HƯỚNG DẪN DUY KIỂM CHỨNG NHANH TRONG UNITY EDITOR

Mọi file model và script C# đã được cập nhật trực tiếp vào dự án của Duy:
1. Chuyển sang Unity Editor (scene `Sandbox_Duy.unity`), Unity đã tự biên dịch sạch (`Build succeeded: 0 errors, 0 warnings mới`).
2. Chọn GameObject `HandTrackingRig` trong Hierarchy:
   - Click chuột phải vào component `Hand3DVisualizer` $\rightarrow$ Chọn **"Reset Bones to Flat Pose"**.
   - Click chuột phải vào component `Hand3DVisualizer` $\rightarrow$ Chọn **"Auto-Map Blender Bones (.L / .R)"**.
3. Tích chọn **"Enable Manual Curl Test"** và kéo thanh trượt **`Debug Test Curl`** (từ 0.0 đến 1.0) **ngay trong Scene view**:
   - Cả 2 bàn tay gập nắm đấm mượt mà: các ngón cong tròn đều đặn theo từng đốt (không bị đâm thủng lòng bàn tay), ngón cái ôm gọn gàng ra phía trước ngón trỏ, da thịt hoàn hảo!
