# BÁO CÁO TIẾN ĐỘ TUẦN — Game đấm khối AR điều khiển bằng cử chỉ tay

> Học phần ED4140 — Đồ án VR/AR · Nhóm: Thái, Duy, Thảo  
> **Cập nhật:** 22/11/2026 (Kết thúc Sprint 1: Nền móng)  
> **Phụ trách phần nhận diện cử chỉ tay & Tay 3D:** Duy

---

## 1. Đề Tài Và Sản Phẩm

- **Đề tài:** Các kỹ thuật hỗ trợ mô hình AI đáp ứng thời gian thực trong xử lý chuỗi hình ảnh.
- **Sản phẩm:** Game phản xạ đấm khối AR trên PC + webcam (lối chơi tham khảo *Move Fast*). Máy bắn phóng các khối hình bay về phía người chơi; hình bay bên nào thì người chơi dùng **tay bên đó**, làm **đúng cử chỉ** yêu cầu để phá khối, ghi điểm và tăng combo. Đối tượng 3D được vẽ chồng lên không gian webcam (AR).
- **Bộ 3 cử chỉ cốt lõi:**
  1. `PUNCH_STRAIGHT` (Đấm thẳng)
  2. `BLOCK` (Đấm thủ / Đỡ đòn)
  3. `OPEN_PALM` (Xoè tay / Đẩy chưởng)
  *(Đã thống nhất loại bỏ cử chỉ đấm móc để tập trung tối ưu độ trễ và độ chính xác cho 3 cử chỉ chính).*

---

## 2. Mục Tiêu Đo Được & Kết Quả Đạt Được Tuần Này

| Chỉ số | Mục tiêu đồ án | Baseline đo được cuối Sprint 1 | Đánh giá hiện trạng |
|---|---|---|---|
| **Độ trễ từng khâu (`recognize`)** | Nhỏ nhất có thể | **p50 ≈ 22 ms**, p95 ≈ 33 ms (trên CPU i5-12450H) | Đạt rất tốt, mô hình chạy nhẹ trên CPU |
| **Độ trễ toàn trình camera $\rightarrow$ Unity** | < 100 ms | **p50 ≈ 24–40 ms** (đo tại Debug HUD Unity) | Vượt mục tiêu ban đầu |
| **Tốc độ khung hình (FPS)** | $\ge$ 25 FPS | **30 FPS** (Đã cấu hình MJPG 720p) | Đạt chuẩn thời gian thực |
| **Số cử chỉ nhận diện được** | Sprint 1: 1 cử chỉ | **Đủ 3 cử chỉ** (`PUNCH_STRAIGHT`, `BLOCK`, `OPEN_PALM`) | **Vượt tiến độ 1 tuần** |
| **Tay 3D trong Unity** | Kế hoạch Sprint 2 | **Đã có Rig tay 3D uốn 15 đốt xương theo UDP** | **Vượt tiến độ 1 tuần** |

---

## 3. Chi Tiết Tiến Độ Thực Hiện Của Duy (Phần Việc Độc Lập)

Trong Sprint 1, Duy phụ trách lát cắt: **Cử chỉ tay (từ nhận diện đến bàn tay trong game)**. Các kết quả cụ thể đã hoàn thành bao gồm:

### 3.1. Thu Thập Dữ Liệu & Gán Nhãn Cử Chỉ
- Xây dựng hoàn chỉnh công cụ thu thập tự động `python/tools/collect_and_label.py`:
  - Cơ chế đếm ngược 3 giây trước khi tự động ghi 50 mẫu liên tiếp cho mỗi thế tay.
  - Phân loại và lưu trữ ảnh sạch (full frame + crop bàn tay) vào thư mục `python/data/dataset_images/`.
  - Trích xuất tự động vector đặc trưng trung bình và lưu thành bộ dữ liệu chuẩn:
    - `python/data/pose_templates.npz`: Vector đặc trưng 63 chiều chuẩn hóa của từng thế tay.
    - `python/data/pose_config.json`: Toàn bộ ngưỡng động học (vận tốc phóng to, tỷ lệ mở ngón tay $r_{open}$).
    - `python/data/gesture_dataset.npz`: Toàn bộ tập dữ liệu mẫu phục vụ kiểm thử và đánh giá sau này.

### 3.2. Thuật Toán Nhận Diện Động Học & Khử Rung Lắc
- **Tích hợp bộ lọc One-Euro (`OneEuroFilter`):** Giải quyết triệt để vấn đề rung lắc (jitter) của toạ độ MediaPipe khi tay đứng yên, đồng thời giữ nguyên phản xạ tức thì, không bị trễ khi người chơi vung tay ra đòn nhanh.
- **Trích xuất đặc trưng động học (`punchar/decision/features.py`):**
  - Tính toán độ lớn bàn tay $hand\_size$ (khoảng cách Landmark 0 cổ tay $\rightarrow$ Landmark 9 gốc ngón giữa).
  - Tính tỷ lệ xòe ngón $r_{open}$ phục vụ phân biệt chính xác thế nắm đấm ($r_{open} \le 1.28$) và xoè tay ($r_{open} \ge 1.48$).
  - Chuẩn hóa phân làn tay Trái / Phải theo đúng góc nhìn soi gương của người chơi.
- **Cài đặt State Machine cho cả 3 thế cử chỉ (`punchar/decision/state_machine.py`):**
  - `PUNCH_STRAIGHT`: Nhận diện cú đấm khi tay nắm kết hợp kích thước bàn tay tăng nhanh $\ge 15\%$ trong cửa sổ $150\text{ ms}$, chuyển trạng thái `IDLE → WINDUP → STRIKE → COOLDOWN`.
  - `BLOCK`: Nhận diện thế thủ khi tay nắm giữ ổn định vị trí trước mặt liên tục trong thời gian $\ge 120\text{ ms}$.
  - `OPEN_PALM`: Nhận diện cú đẩy tay khi lòng bàn tay mở rộng và đẩy về phía trước camera.
  - Bộ kiểm thử tự động `tests/test_decision.py` đã vượt qua 100% (6/6 test cases).

### 3.3. Dựng Rig Bàn Tay 3D Trong Unity (Vượt Tiến Độ Kế Hoạch Sprint 2)
- Nhập cặp model bàn tay FBX vào Unity (`Assets/Duy_Hand3D/Models/`).
- Viết script điều khiển uốn gập xương [Hand3DVisualizer.cs](file:///D:/CODE/CODE/2026.1/DoAn_VRAR/punchAR/Assets/Duy_Hand3D/Scripts/Visuals/Hand3DVisualizer.cs):
  - Tự động bắt cặp và ánh xạ 15 đốt xương ngón tay (3 đốt cho mỗi ngón: Cái, Trỏ, Giữa, Áp út, Út).
  - Tính toán góc gập hình học thực tế từ 21 điểm landmark 3D nhận qua UDP để xoay xương cục bộ mượt mà.
  - Tự động vô hiệu hoá các Animator thừa của file FBX để giải phóng khớp xương.
- Viết module nhận mạng UDP luồng nền độc lập [UdpHandProvider.cs](file:///D:/CODE/CODE/2026.1/DoAn_VRAR/punchAR/Assets/Duy_Hand3D/Scripts/Providers/UdpHandProvider.cs), parse mảng phẳng 63 float `lm` mà không gây drop frame Unity.
- Thiết lập màn hình Debug HUD [Hand3DDebugOverlay.cs](file:///D:/CODE/CODE/2026.1/DoAn_VRAR/punchAR/Assets/Duy_Hand3D/Scripts/Debug/Hand3DDebugOverlay.cs) đo trực tiếp tần số gói tin (PPS $\approx 30$) và độ trễ toàn trình.

---

## 4. Các Hạn Chế Kỹ Thuật Thực Tế & Đề Xuất Hỗ Trợ

Trong quá trình thực nghiệm đưa bàn tay lên không gian 3D Unity, Duy ghi nhận 3 vấn đề kỹ thuật lớn cần chia sẻ và phối hợp cùng nhóm:

1. **Trục xoay cổ tay 3D (Wrist Rotation) chưa chuẩn hoá:**
   - *Nguyên nhân:* Hệ toạ độ tương đối của MediaPipe (camera space) không đồng trục với tư thế gốc (bind pose / rest pose) của mô hình bàn tay FBX xuất từ Blender.
   - *Ứng phó tạm thời:* Tắt chế độ xoay cổ tay tự động, chỉ cho bàn tay tịnh tiến vị trí và uốn 15 đốt ngón tay để đảm bảo chuyển động ổn định không bị vặn xoắn.
2. **Mô hình bàn tay trái bị lỗi ngược trục xương uốn (`LeftHand_FromRight`):**
   - *Nguyên nhân:* File `LeftHand.fbx` có trục uốn xương cục bộ (local bend axis) trong Blender bị ngược hướng so với `RightHand.fbx`, khiến ngón tay trái khi gập bị quặp ngược ra sau.
   - *Ứng phó tạm thời của Duy:* Dùng bản sao của `RightHand.fbx` làm đại diện cho tay trái (`LeftHand_FromRight`), viết hàm auto-map hậu tố xương `.R` cho cả hai tay.
   - *Đề xuất hỗ trợ:* **Cần bạn có chuyên môn Blender hỗ trợ mở file 3D gốc để export lại cặp bàn tay đối xứng chuẩn (X-Axis Mirror có roll xương đồng nhất)**.
3. **Sự sai lệch vị trí giữa ảnh OpenCV và màn hình Unity:**
   - *Độ sâu Z:* Bàn tay 3D hiện bị neo trên mặt phẳng phẳng $Z = 2.0\text{ m}$, chưa phản ánh khoảng cách xa/gần thực tế của cú đấm.
   - *Vùng bao (Play Area) vs FOV:* Tầm với bàn tay trên OpenCV (ảnh 2D phẳng) chưa khớp hoàn toàn với góc nhìn camera 3D trong Unity.
   - *Lệch gốc xương:* Điểm định vị từ MediaPipe là Landmark 9 (tâm bàn tay), trong khi Transform gốc của model Unity lại nằm ở Cổ tay (Wrist), gây ra một khoảng dịch tịnh tiến nhẹ.
   - *Căn khớp AR:* Cần chờ Thái hoàn thiện lớp nền webcam AR ở Sprint 2 để có video nền thực tế căn khớp vị trí tay ảo đè lên tay thật.

---

## 5. Kế Hoạch Sprint 2 Của Duy (23/11 – 29/11)

- **Phối hợp với Thái (Lớp AR):** Đồng bộ toạ độ bàn tay 3D đè khớp chính xác lên hình ảnh webcam người thật khi lớp nền AR được đưa vào Unity.
- **Phối hợp với Thảo (Gameplay):**
  - Đóng gói toàn bộ Rig bàn tay 3D thành Prefab chuẩn giao cho Thảo đưa vào scene chính `Main.unity`.
  - Nối sự kiện `OnStrikeDetected` từ tay 3D vào hệ thống va chạm để khi đấm trúng khối bay tới thì khối vỡ vụn và tính điểm combo.
- **Tối ưu nhận diện:** Chạy benchmark đo đạc độ chính xác (Precision / Recall) và tỉ lệ kích hoạt nhầm trên tập dữ liệu 20 cú đấm thực tế.
