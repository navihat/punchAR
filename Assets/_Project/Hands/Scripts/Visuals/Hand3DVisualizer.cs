using System;
using UnityEngine;

namespace PunchAR.Hand3D
{
    [Serializable]
    public class HandRigConfig
    {
        [Tooltip("Đối tượng gốc (LeftHand_Root hoặc RightHand_Root)")]
        public Transform root;

        [Header("15 đốt xương (Đốt 01 -> 02 -> 03)")]
        public Transform[] thumb = new Transform[3];
        public Transform[] index = new Transform[3];
        public Transform[] middle = new Transform[3];
        public Transform[] ring = new Transform[3];
        public Transform[] pinky = new Transform[3];

        [Header("Trục gập cục bộ 4 ngón (Chỉ đặt Direction là 1 hoặc -1)")]
        public Vector3 fingerBendAxis = new Vector3(1f, 0f, 0f);
        public float fingerBendDirection = 1f;

        [Header("Trục gập ngón cái Đốt 01 CMC (Khép vào lòng bàn tay)")]
        public Vector3 thumbCmcBendAxis = new Vector3(0f, 0f, 1f);
        public float thumbCmcBendDirection = 1f;

        [Header("Trục gập ngón cái Đốt 02 MCP & 03 IP (Gập bản lề)")]
        public Vector3 thumbBendAxis = new Vector3(1f, 0f, 0f);
        public float thumbBendDirection = 1f;

        [Header("Hiệu chỉnh góc xoay cổ tay 3D (khi bật Enable Wrist Rotation)")]
        public Vector3 wristRotationOffset = Vector3.zero;

        [NonSerialized] public Quaternion[] thumbInitRot = new Quaternion[3];
        [NonSerialized] public Quaternion[] indexInitRot = new Quaternion[3];
        [NonSerialized] public Quaternion[] middleInitRot = new Quaternion[3];
        [NonSerialized] public Quaternion[] ringInitRot = new Quaternion[3];
        [NonSerialized] public Quaternion[] pinkyInitRot = new Quaternion[3];
        [NonSerialized] public Quaternion rootInitRot = Quaternion.identity;
        [NonSerialized] public bool isInitialized;

        public void CacheInitialRotations(string handLabel)
        {
            if (root != null)
            {
                rootInitRot = root.rotation;

                // Tự động kiểm tra Scale biến dạng (tránh lỗi bẹp Y=0 hoặc Scale âm)
                foreach (Transform child in root)
                {
                    if (Mathf.Abs(child.localScale.y) < 0.001f || Mathf.Abs(child.localScale.x) < 0.001f || Mathf.Abs(child.localScale.z) < 0.001f)
                    {
                        Debug.LogError($"[Hand3DVisualizer] LỖI BIẾN DẠNG: Model con '{child.name}' của '{root.name}' ({handLabel}) có Scale bị triệt tiêu về 0 ({child.localScale})! Cần đặt lại Scale (5, 5, 5) trong Unity Inspector.");
                    }
                    else if (child.localScale.z < 0 || child.localScale.x < 0)
                    {
                        Debug.LogWarning($"[Hand3DVisualizer] CẢNH BÁO: Model con '{child.name}' của '{root.name}' ({handLabel}) có Scale âm ({child.localScale})! Điều này sẽ làm đảo lộn chiều gập ngón tay và pháp tuyến 3D.");
                    }
                }

                // Tự động vô hiệu hoá Animator thừa trên model FBX để không khóa cứng khớp xương
                Animator[] animators = root.GetComponentsInChildren<Animator>(true);
                foreach (Animator anim in animators)
                {
                    if (anim.enabled)
                    {
                        anim.enabled = false;
                        Debug.LogWarning($"[Hand3DVisualizer] Đã tự động tắt Animator thừa trên '{anim.gameObject.name}' ({handLabel}) để mở khóa khớp ngón tay.");
                    }
                }
            }

            int missing = 0;
            missing += CacheChain(thumb, thumbInitRot);
            missing += CacheChain(index, indexInitRot);
            missing += CacheChain(middle, middleInitRot);
            missing += CacheChain(ring, ringInitRot);
            missing += CacheChain(pinky, pinkyInitRot);

            if (missing > 0)
            {
                Debug.LogWarning($"[Hand3DVisualizer] Tay {handLabel} đang thiếu {missing}/15 đốt xương! Hãy bấm chuột phải lên script -> 'Auto-Map Blender Bones (.L / .R)'.");
            }

            isInitialized = true;
        }

        private int CacheChain(Transform[] bones, Quaternion[] cache)
        {
            int missingCount = 0;
            if (bones == null) return 3;
            for (int i = 0; i < 3; i++)
            {
                if (i < bones.Length && bones[i] != null)
                {
                    // Lưu đúng Rest Pose thật sự của FBX Bind Pose (CẤM gán Quaternion.identity)
                    cache[i] = bones[i].localRotation;
                }
                else
                {
                    cache[i] = Quaternion.identity;
                    missingCount++;
                }
            }
            return missingCount;
        }
    }

    public class Hand3DVisualizer : MonoBehaviour
    {
        [Header("1. Nguồn cấp dữ liệu (Kéo UdpHandProvider vào đây)")]
        [SerializeField] private MonoBehaviour providerSource;
        private IHandInputProvider _provider;

        [Header("2. Ánh xạ Không gian 3D & Giới hạn Khung nhìn (Movement Bounds)")]
        [Tooltip("Bật để chiếu thẳng theo khung hình Main Camera; Tắt để dùng PlayWidth / PlayHeight cố định")]
        [SerializeField] private bool useCameraViewportMapping = false;
        [Tooltip("Khoảng lề an toàn ở rìa khung hình camera (tránh bàn tay bay ra mép màn hình)")]
        [SerializeField] private Vector2 viewportMargin = new Vector2(0.08f, 0.08f);
        [Tooltip("Khoảng cách Z tối thiểu tới Camera để tránh đâm xuyên mặt kính")]
        [SerializeField] private float minCameraDepth = 0.5f;
        [SerializeField] private float playWidth = 4.0f;
        [SerializeField] private float playHeight = 2.5f;
        [SerializeField] private float centerY = 1.0f;
        [SerializeField] private float hitPlaneZ = 2.0f;
        [SerializeField] private float positionSmoothSpeed = 35f;
        [SerializeField] private float rotationSmoothSpeed = 20f;
        [SerializeField] private float jointSmoothSpeed = 26f;
        [SerializeField] private bool hideHandsWhenLost = true;

        [Header("3. Xoay cổ tay 3D & Độ nhạy gập ngón")]
        [SerializeField] private bool enableWristRotation = true;
        [Tooltip("Hệ số khuếch đại góc gập ngón tay (khuyên dùng 1.25)")]
        [SerializeField] private float fingerBendGain = 1.25f;
        [SerializeField] private float mcpRestOffsetDeg = 0f;
        [SerializeField] private float thumbCmcRestOffsetDeg = 10f;
        [Tooltip("Biên độ gập tối đa từng đốt 4 ngón: X=MCP (01), Y=PIP (02), Z=DIP (03)")]
        [SerializeField] private Vector3 fingerMaxBendDeg = new Vector3(80f, 95f, 65f);
        [Tooltip("Biên độ gập tối đa ngón cái: X=CMC (01), Y=MCP (02), Z=IP (03)")]
        [SerializeField] private Vector3 thumbMaxBendDeg = new Vector3(35f, 45f, 55f);
        [Range(0f, 1f)]
        [Tooltip("Tỷ lệ gập khi nhận diện Closed_Fist mà không có 21 landmarks")]
        [SerializeField] private float fallbackFistRatio = 0.9f;

        [Header("4. Hiệu ứng Lao Nắm Đấm (+Z)")]
        [SerializeField] private float punchLungeZ = 0.35f;
        [SerializeField] private float lungeReturnSpeed = 14f;

        [Header("5. Test nhanh trục gập khớp (Tắt đi khi chạy Webcam thật)")]
        [SerializeField] private bool enableManualCurlTest = false;
        [Range(0f, 1f)]
        [SerializeField] private float debugTestCurl = 0f;

        [Header("6. Cấu hình Rig Tay Trái & Tay Phải")]
        public HandRigConfig leftHandRig = new HandRigConfig();
        public HandRigConfig rightHandRig = new HandRigConfig();

        private float _leftLungeOffset;
        private float _rightLungeOffset;

        public Vector3 LeftHandWorldPos => leftHandRig.root != null ? leftHandRig.root.position : Vector3.zero;
        public Vector3 RightHandWorldPos => rightHandRig.root != null ? rightHandRig.root.position : Vector3.zero;

        private void Awake()
        {
            _provider = providerSource as IHandInputProvider ?? GetComponent<IHandInputProvider>();
            if (_provider == null && Application.isPlaying)
            {
                Debug.LogError("[Hand3DVisualizer] Chưa gắn UdpHandProvider!");
            }

            // Tự động kiểm tra và dọn dẹp model con trùng lặp (LeftHand_FromRight)
            CleanupDuplicateChildModels();

            // Self-healing: Tự động chạy AutoMapBlenderBones nếu phát hiện slot xương bị null
            if (leftHandRig.thumb[0] == null || rightHandRig.thumb[0] == null ||
                leftHandRig.index[0] == null || rightHandRig.index[0] == null)
            {
                AutoMapBlenderBones();
            }

            // Đồng bộ góc xoay mô hình con để ngón tay hướng +Z (Root) và mu bàn tay hướng +Y (Root)
            AlignChildModelRotation(leftHandRig.root, "LeftHand", LeftModelEuler);
            AlignChildModelRotation(rightHandRig.root, "RightHand", RightModelEuler);

            leftHandRig.CacheInitialRotations("Left");
            rightHandRig.CacheInitialRotations("Right");
        }

        private void OnEnable()
        {
            if (_provider != null) _provider.OnStrikeDetected += OnStrike;
        }

        private void OnDisable()
        {
            if (_provider != null) _provider.OnStrikeDetected -= OnStrike;
        }

        private void OnStrike(string hand, string kind, Vector2 normPos, long tsMs)
        {
            if (kind == "PUNCH_STRAIGHT" || kind == "OPEN_PALM")
            {
                if (hand == "Left") _leftLungeOffset = punchLungeZ;
                else if (hand == "Right") _rightLungeOffset = punchLungeZ;
            }
        }

        private void Update()
        {
            if (enableManualCurlTest)
            {
                ApplyTestCurl(leftHandRig, debugTestCurl);
                ApplyTestCurl(rightHandRig, debugTestCurl);
                return;
            }

            if (!Application.isPlaying || _provider == null) return;

            _leftLungeOffset = Mathf.Lerp(_leftLungeOffset, 0f, Time.deltaTime * lungeReturnSpeed);
            _rightLungeOffset = Mathf.Lerp(_rightLungeOffset, 0f, Time.deltaTime * lungeReturnSpeed);

            UpdateHandVisual(_provider.LeftHand, leftHandRig, isLeft: true, _leftLungeOffset);
            UpdateHandVisual(_provider.RightHand, rightHandRig, isLeft: false, _rightLungeOffset);
        }

        private void ApplyTestCurl(HandRigConfig rig, float ratio)
        {
            if (rig == null || rig.root == null) return;
            if (!rig.root.gameObject.activeSelf) rig.root.gameObject.SetActive(true);
            if (!rig.isInitialized) rig.CacheInitialRotations("Test");

            float r = Mathf.Clamp01(ratio);

            // Ngón cái 3 đốt: CMC (01), MCP (02), IP (03)
            if (rig.thumb != null && rig.thumb.Length >= 3 && rig.thumbInitRot != null && rig.thumbInitRot.Length >= 3)
            {
                RotateBoneRelative(rig.thumb[0], rig.thumbInitRot[0], thumbMaxBendDeg.x * r, rig.thumbCmcBendAxis, rig.thumbCmcBendDirection);
                RotateBoneRelative(rig.thumb[1], rig.thumbInitRot[1], thumbMaxBendDeg.y * r, rig.thumbBendAxis, rig.thumbBendDirection);
                RotateBoneRelative(rig.thumb[2], rig.thumbInitRot[2], thumbMaxBendDeg.z * r, rig.thumbBendAxis, rig.thumbBendDirection);
            }

            // 4 ngón còn lại
            ApplyFingerCurlRatio(rig.index, rig.indexInitRot, r, rig.fingerBendAxis, rig.fingerBendDirection);
            ApplyFingerCurlRatio(rig.middle, rig.middleInitRot, r, rig.fingerBendAxis, rig.fingerBendDirection);
            ApplyFingerCurlRatio(rig.ring, rig.ringInitRot, r, rig.fingerBendAxis, rig.fingerBendDirection);
            ApplyFingerCurlRatio(rig.pinky, rig.pinkyInitRot, r, rig.fingerBendAxis, rig.fingerBendDirection);
        }

        private void ApplyFingerCurlRatio(Transform[] bones, Quaternion[] initRots, float r, Vector3 axis, float dir)
        {
            if (bones == null || initRots == null) return;
            if (bones.Length > 0 && bones[0] != null) RotateBoneRelative(bones[0], initRots[0], fingerMaxBendDeg.x * r, axis, dir);
            if (bones.Length > 1 && bones[1] != null) RotateBoneRelative(bones[1], initRots[1], fingerMaxBendDeg.y * r, axis, dir);
            if (bones.Length > 2 && bones[2] != null) RotateBoneRelative(bones[2], initRots[2], fingerMaxBendDeg.z * r, axis, dir);
        }

        private void UpdateHandVisual(HandFrameData data, HandRigConfig rig, bool isLeft, float zOffset)
        {
            if (rig == null || rig.root == null) return;

            if (!data.isTracked)
            {
                if (hideHandsWhenLost && rig.root.gameObject.activeSelf)
                {
                    rig.root.gameObject.SetActive(false);
                }
                return;
            }

            if (!rig.root.gameObject.activeSelf) rig.root.gameObject.SetActive(true);

            // 1. Di chuyển vị trí bàn tay trên mặt phẳng Hit Plane (có khóa biên an toàn)
            Vector3 targetPos = MapNormalizedToWorld(data.palmPos.x, data.palmPos.y, zOffset);
            rig.root.position = Vector3.Lerp(rig.root.position, targetPos, Time.deltaTime * positionSmoothSpeed);

            if (!rig.isInitialized) rig.CacheInitialRotations(isLeft ? "Left" : "Right");

            // 2. Xoay cổ tay & gập 15 đốt ngón tay theo 21 điểm 3D world_landmarks
            if (data.hasLandmarks && data.landmarks != null && data.landmarks.Length == 21)
            {
                if (enableWristRotation)
                {
                    ApplyWristOrientation(data.landmarks, rig, isLeft);
                }
                else
                {
                    rig.root.rotation = Quaternion.Slerp(rig.root.rotation, rig.rootInitRot, Time.deltaTime * rotationSmoothSpeed);
                }

                ApplyThumbChain(data.landmarks, rig);
                ApplyFingerChain(data.landmarks, 0, 5, 6, 7, 8, rig.index, rig.indexInitRot, rig.fingerBendAxis, rig.fingerBendDirection);
                ApplyFingerChain(data.landmarks, 0, 9, 10, 11, 12, rig.middle, rig.middleInitRot, rig.fingerBendAxis, rig.fingerBendDirection);
                ApplyFingerChain(data.landmarks, 0, 13, 14, 15, 16, rig.ring, rig.ringInitRot, rig.fingerBendAxis, rig.fingerBendDirection);
                ApplyFingerChain(data.landmarks, 0, 17, 18, 19, 20, rig.pinky, rig.pinkyInitRot, rig.fingerBendAxis, rig.fingerBendDirection);
            }
            else
            {
                float r = data.shape == "Closed_Fist" ? fallbackFistRatio : 0f;
                ApplyTestCurl(rig, r);
            }
        }

        private void ApplyWristOrientation(Vector3[] lm, HandRigConfig rig, bool isLeft)
        {
            Vector3 p0 = ToUnityHandSpace(lm[0]);   // Cổ tay
            Vector3 p5 = ToUnityHandSpace(lm[5]);   // Gốc ngón trỏ
            Vector3 p9 = ToUnityHandSpace(lm[9]);   // Gốc ngón giữa
            Vector3 p17 = ToUnityHandSpace(lm[17]); // Gốc ngón út

            Vector3 handForward = (p9 - p0).normalized;
            Vector3 handAcross = isLeft ? (p5 - p17).normalized : (p17 - p5).normalized;
            Vector3 palmNormal = Vector3.Cross(handAcross, handForward).normalized;

            if (handForward.sqrMagnitude > 0.0001f && palmNormal.sqrMagnitude > 0.0001f)
            {
                // Ngón tay hướng về phía trước (+Z), mu bàn tay hướng lên (+Y)
                Quaternion targetWorldRot = Quaternion.LookRotation(handForward, -palmNormal)
                                            * Quaternion.Euler(rig.wristRotationOffset);

                // Đảm bảo Slerp luôn đi theo đường cung ngắn nhất, ngăn lật 180 độ giật cục
                if (Quaternion.Dot(rig.root.rotation, targetWorldRot) < 0f)
                {
                    targetWorldRot = new Quaternion(-targetWorldRot.x, -targetWorldRot.y, -targetWorldRot.z, -targetWorldRot.w);
                }

                rig.root.rotation = Quaternion.Slerp(rig.root.rotation, targetWorldRot, Time.deltaTime * rotationSmoothSpeed);
            }
        }

        public static Vector3 ToUnityHandSpace(Vector3 p)
        {
            // MediaPipe quy ước Z càng nhỏ càng gần camera; trong Unity thế giới AR, khối bay về camera,
            // đấm thẳng tới khối là hướng +Z, do đó đảo dấu Z (-p.z).
            return new Vector3(p.x, p.y, -p.z);
        }

        public Vector3 MapNormalizedToWorld(float xUdp, float yUdp, float zOffset = 0f)
        {
            if (useCameraViewportMapping && Camera.main != null)
            {
                float clampedX = Mathf.Clamp(xUdp, viewportMargin.x, 1f - viewportMargin.x);
                float clampedY = Mathf.Clamp(yUdp, viewportMargin.y, 1f - viewportMargin.y);
                float depth = Mathf.Max(minCameraDepth, hitPlaneZ + zOffset);
                return Camera.main.ViewportToWorldPoint(new Vector3(clampedX, clampedY, depth));
            }

            float clampedNormX = Mathf.Clamp01(xUdp);
            float clampedNormY = Mathf.Clamp01(yUdp);
            float worldX = (clampedNormX - 0.5f) * playWidth;
            float worldY = (clampedNormY - 0.5f) * playHeight + centerY;
            return new Vector3(worldX, worldY, hitPlaneZ + zOffset);
        }

        private void ApplyThumbChain(Vector3[] lm, HandRigConfig rig)
        {
            if (rig.thumb == null || rig.thumb.Length < 3) return;

            Vector3 p0 = ToUnityHandSpace(lm[0]);
            Vector3 p1 = ToUnityHandSpace(lm[1]);
            Vector3 p2 = ToUnityHandSpace(lm[2]);
            Vector3 p3 = ToUnityHandSpace(lm[3]);
            Vector3 p4 = ToUnityHandSpace(lm[4]);

            float a1 = CalcBendAngleDeg(p0, p1, p2, thumbCmcRestOffsetDeg, thumbMaxBendDeg.x);
            float a2 = CalcBendAngleDeg(p1, p2, p3, 5f, thumbMaxBendDeg.y);
            float a3 = CalcBendAngleDeg(p2, p3, p4, 3f, thumbMaxBendDeg.z);

            RotateBoneRelative(rig.thumb[0], rig.thumbInitRot[0], a1, rig.thumbCmcBendAxis, rig.thumbCmcBendDirection);
            RotateBoneRelative(rig.thumb[1], rig.thumbInitRot[1], a2, rig.thumbBendAxis, rig.thumbBendDirection);
            RotateBoneRelative(rig.thumb[2], rig.thumbInitRot[2], a3, rig.thumbBendAxis, rig.thumbBendDirection);
        }

        private void ApplyFingerChain(
            Vector3[] lm, int wrist, int p1, int p2, int p3, int p4,
            Transform[] bones, Quaternion[] initRots, Vector3 axis, float dir)
        {
            if (bones == null || bones.Length < 3) return;

            Vector3 v0 = ToUnityHandSpace(lm[wrist]);
            Vector3 v1 = ToUnityHandSpace(lm[p1]);
            Vector3 v2 = ToUnityHandSpace(lm[p2]);
            Vector3 v3 = ToUnityHandSpace(lm[p3]);
            Vector3 v4 = ToUnityHandSpace(lm[p4]);

            float a1 = CalcBendAngleDeg(v0, v1, v2, mcpRestOffsetDeg, fingerMaxBendDeg.x);
            float a2 = CalcBendAngleDeg(v1, v2, v3, 2f, fingerMaxBendDeg.y);
            float a3 = CalcBendAngleDeg(v2, v3, v4, 2f, fingerMaxBendDeg.z);

            RotateBoneRelative(bones[0], initRots[0], a1, axis, dir);
            RotateBoneRelative(bones[1], initRots[1], a2, axis, dir);
            RotateBoneRelative(bones[2], initRots[2], a3, axis, dir);
        }

        private void RotateBoneRelative(
            Transform bone, Quaternion initRot, float angleDeg, Vector3 axis, float dir)
        {
            if (bone == null || axis.sqrMagnitude < 0.0001f) return;
            float clampedDir = Mathf.Sign(dir == 0f ? 1f : dir);
            Quaternion delta = Quaternion.AngleAxis(angleDeg * clampedDir, axis.normalized);
            Quaternion targetRot = initRot * delta;
            if (Application.isPlaying)
            {
                bone.localRotation = Quaternion.Slerp(bone.localRotation, targetRot, Time.deltaTime * jointSmoothSpeed);
            }
            else
            {
                bone.localRotation = targetRot;
            }
        }

        private float CalcBendAngleDeg(Vector3 a, Vector3 b, Vector3 c, float restOffsetDeg, float maxBendLimit)
        {
            Vector3 v1 = (a - b).normalized;
            Vector3 v2 = (c - b).normalized;
            float rawBend = 180f - Vector3.Angle(v1, v2);
            float adjusted = Mathf.Max(0f, rawBend - restOffsetDeg) * fingerBendGain;
            return Mathf.Clamp(adjusted, 0f, maxBendLimit);
        }

        [ContextMenu("Reset Bones to Flat Pose")]
        public void ResetBonesToFlatPose()
        {
            enableManualCurlTest = false;
            debugTestCurl = 0f;
            ResetRigToRest(leftHandRig);
            ResetRigToRest(rightHandRig);
            Debug.Log("[Hand3DVisualizer] Đã reset toàn bộ khớp ngón tay 2 bàn tay về vị trí duỗi thẳng ban đầu.");
        }

        private void ResetRigToRest(HandRigConfig rig)
        {
            if (rig == null) return;
            ResetChain(rig.thumb, rig.thumbInitRot);
            ResetChain(rig.index, rig.indexInitRot);
            ResetChain(rig.middle, rig.middleInitRot);
            ResetChain(rig.ring, rig.ringInitRot);
            ResetChain(rig.pinky, rig.pinkyInitRot);
        }

        private void ResetChain(Transform[] bones, Quaternion[] initRots)
        {
            if (bones == null || initRots == null) return;
            for (int i = 0; i < Mathf.Min(bones.Length, initRots.Length); i++)
            {
                if (bones[i] != null && initRots[i] != Quaternion.identity)
                {
                    bones[i].localRotation = initRots[i];
                }
            }
        }

        [ContextMenu("Fix Hierarchy: Remove Duplicate Child Models")]
        public void CleanupDuplicateChildModels()
        {
            CleanupRootChildren(leftHandRig.root, "LeftHand", "LeftHand_FromRight");
            CleanupRootChildren(rightHandRig.root, "RightHand", null);
        }

        private void CleanupRootChildren(Transform root, string primaryModelName, string duplicateNamePattern)
        {
            if (root == null) return;
            System.Collections.Generic.List<Transform> toRemove = new System.Collections.Generic.List<Transform>();
            foreach (Transform child in root)
            {
                if (!string.IsNullOrEmpty(duplicateNamePattern) &&
                    child.name.IndexOf(duplicateNamePattern, StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    toRemove.Add(child);
                }
            }
            foreach (var t in toRemove)
            {
                Debug.LogWarning($"[Hand3DVisualizer] Đã tự động xóa bỏ model con trùng lặp '{t.name}' dưới '{root.name}'.");
                if (Application.isPlaying)
                {
                    Destroy(t.gameObject);
                }
                else
                {
#if UNITY_EDITOR
                    DestroyImmediate(t.gameObject);
#endif
                }
            }
        }

        [ContextMenu("Wipe Bone Transform Overrides & Revert to Clean Rest Pose")]
        public void WipeBoneOverridesAndRevertToRestPose()
        {
            WipeRigBones(leftHandRig);
            WipeRigBones(rightHandRig);
            debugTestCurl = 0f;
#if UNITY_EDITOR
            UnityEditor.EditorUtility.SetDirty(gameObject);
            if (!Application.isPlaying)
            {
                UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(gameObject.scene);
            }
#endif
            Debug.Log("[Hand3DVisualizer] Đã xóa sạch mọi dirty override trên 30 đốt xương, đưa cả 2 bàn tay về thế mở phẳng (Flat Open Rest Pose).");
        }

        private void WipeRigBones(HandRigConfig rig)
        {
            if (rig == null) return;
            WipeChain(rig.thumb);
            WipeChain(rig.index);
            WipeChain(rig.middle);
            WipeChain(rig.ring);
            WipeChain(rig.pinky);
        }

        private void WipeChain(Transform[] bones)
        {
            if (bones == null) return;
            foreach (var b in bones)
            {
                if (b != null)
                {
#if UNITY_EDITOR
                    UnityEditor.PrefabUtility.RevertPropertyOverride(
                        new UnityEditor.SerializedObject(b).FindProperty("m_LocalRotation"),
                        UnityEditor.InteractionMode.AutomatedAction
                    );
#endif
                }
            }
        }

        [ContextMenu("Auto-Map Blender Bones (.L / .R)")]
        public void AutoMapBlenderBones()
        {
            // Tự động nhận diện hậu tố .L hoặc .R
            MapRigAutoSuffix(leftHandRig, ".L", ".R");
            MapRigAutoSuffix(rightHandRig, ".R", ".L");

            // Thiết lập mặc định trục gập chuẩn theo số liệu đo đạc độc lập Blender CLI:
            // TAY TRÁI (LeftHand):
            // - 4 ngón dài: gập quanh Vector3.right theo chiều -1f
            leftHandRig.fingerBendAxis = Vector3.right;
            leftHandRig.fingerBendDirection = -1f;
            // - Ngón cái CMC (.01): quét quanh Vector3.forward (Z) theo chiều +1f để quét ngang trước lòng bàn tay
            leftHandRig.thumbCmcBendAxis = Vector3.forward;
            leftHandRig.thumbCmcBendDirection = 1f;
            // - Ngón cái MCP/IP (.02, .03): gập đầu ngón quanh Vector3.right theo chiều +1f ôm vào nắm đấm
            leftHandRig.thumbBendAxis = Vector3.right;
            leftHandRig.thumbBendDirection = 1f;

            // TAY PHẢI (RightHand):
            // - 4 ngón dài: gập quanh Vector3.right theo chiều +1f
            rightHandRig.fingerBendAxis = Vector3.right;
            rightHandRig.fingerBendDirection = 1f;
            // - Ngón cái CMC (.01): quét quanh Vector3.forward (Z) theo chiều -1f để quét ngang trước lòng bàn tay
            rightHandRig.thumbCmcBendAxis = Vector3.forward;
            rightHandRig.thumbCmcBendDirection = -1f;
            // - Ngón cái MCP/IP (.02, .03): gập đầu ngón quanh Vector3.right theo chiều +1f ôm vào nắm đấm
            rightHandRig.thumbBendAxis = Vector3.right;
            rightHandRig.thumbBendDirection = 1f;

            // Căn chỉnh góc xoay mô hình con để ngón tay hướng +Z (Root) và mu bàn tay hướng +Y (Root)
            AlignChildModelRotation(leftHandRig.root, "LeftHand", LeftModelEuler);
            AlignChildModelRotation(rightHandRig.root, "RightHand", RightModelEuler);

            Debug.Log("[Hand3DVisualizer] Đã tự động ánh xạ 30 đốt xương và cài đặt trục gập chuẩn: 4 ngón (L=-1, R=+1), CMC (L=+1, R=-1 quanh Z), MCP/IP (+1 quanh X).");
        }

        // LeftHand.fbx là ảnh gương của RightHand.fbx qua trục X, nên góc tay trái = góc tay phải lật gương qua X:
        // R_trái = N · R_phải · N (N = lật X) -> Euler (0, -90, 180) thành (0, 90, 180).
        // Góc cũ (0, -90, 0) cho ngón tay đúng hướng nhưng lật 180° quanh trục ngón (lòng/mu bàn tay bị đảo).
        private static readonly Vector3 RightModelEuler = new Vector3(0f, -90f, 180f);
        private static readonly Vector3 LeftModelEuler = new Vector3(0f, 90f, 180f);

        private void AlignChildModelRotation(Transform root, string modelName, Vector3 targetEuler)
        {
            if (root == null) return;
            foreach (Transform child in root)
            {
                if (child.name.IndexOf(modelName, StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    // Cổ tay (xương hand.L / hand.R) nằm ở gốc FBX: đặt model trùng gốc Root để xoay quanh cổ tay.
                    // Prefab đang lưu LeftHand ở x = -1 (sót từ bản FBX cũ chưa căn giữa), làm tay trái lệch và văng vòng khi xoay.
                    child.localPosition = Vector3.zero;
                    child.localEulerAngles = targetEuler;
                    Debug.Log($"[Hand3DVisualizer] Đã tự động đặt góc xoay mô hình '{child.name}' về {targetEuler}.");
                    return;
                }
            }
        }

        private void MapRigAutoSuffix(HandRigConfig rig, string primarySuffix, string fallbackSuffix)
        {
            if (rig == null || rig.root == null) return;

            string suffix = HasAnyBoneWithSuffix(rig.root, primarySuffix) ? primarySuffix : fallbackSuffix;
            rig.thumb  = FindChainAliases(rig.root, new[] { "thumb", "finger_thumb" }, suffix);
            rig.index  = FindChainAliases(rig.root, new[] { "finger_index", "index", "f_index" }, suffix);
            rig.middle = FindChainAliases(rig.root, new[] { "finger_middle", "middle", "f_middle" }, suffix);
            rig.ring   = FindChainAliases(rig.root, new[] { "finger_ring", "ring", "f_ring" }, suffix);
            rig.pinky  = FindChainAliases(rig.root, new[] { "finger_pinky", "pinky", "f_pinky", "finger_little", "little" }, suffix);
        }

        private bool HasAnyBoneWithSuffix(Transform root, string suffix)
        {
            Transform[] allChildren = root.GetComponentsInChildren<Transform>(true);
            foreach (Transform t in allChildren)
            {
                if (t.name.EndsWith(suffix, StringComparison.OrdinalIgnoreCase))
                    return true;
            }
            return false;
        }

        private Transform[] FindChainAliases(Transform root, string[] prefixes, string suffix)
        {
            Transform[] result = new Transform[3];
            Transform[] allChildren = root.GetComponentsInChildren<Transform>(true);

            for (int i = 0; i < 3; i++)
            {
                string num = $"0{i + 1}";
                foreach (string prefix in prefixes)
                {
                    string exactDot = $"{prefix}.{num}{suffix}";
                    string exactUnder = $"{prefix}_{num}{suffix}";
                    foreach (Transform t in allChildren)
                    {
                        if (string.Equals(t.name, exactDot, StringComparison.OrdinalIgnoreCase) ||
                            string.Equals(t.name, exactUnder, StringComparison.OrdinalIgnoreCase))
                        {
                            result[i] = t;
                            break;
                        }
                    }
                    if (result[i] != null) break;
                }
            }
            return result;
        }
    }
}
