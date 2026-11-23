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

        [Header("Trục gập cục bộ (Chỉ đặt Direction là 1 hoặc -1)")]
        public Vector3 fingerBendAxis = new Vector3(1f, 0f, 0f);
        public float fingerBendDirection = 1f;

        public Vector3 thumbBendAxis = new Vector3(0f, 0f, 1f);
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

        [Header("2. Ánh xạ Không gian 3D & Mặt phẳng Đánh (Hit Plane)")]
        [Tooltip("Bật để chiếu thẳng theo khung hình Main Camera; Tắt để dùng PlayWidth / PlayHeight cố định")]
        [SerializeField] private bool useCameraViewportMapping = false;
        [SerializeField] private float playWidth = 4.0f;
        [SerializeField] private float playHeight = 2.5f;
        [SerializeField] private float centerY = 1.0f;
        [SerializeField] private float hitPlaneZ = 2.0f;
        [SerializeField] private float positionSmoothSpeed = 35f;
        [SerializeField] private float rotationSmoothSpeed = 20f;
        [SerializeField] private float jointSmoothSpeed = 26f;
        [SerializeField] private bool hideHandsWhenLost = true;

        [Header("3. Xoay cổ tay 3D & Độ nhạy gập ngón (Khép kín nắm đấm)")]
        [SerializeField] private bool enableWristRotation = true;
        [SerializeField] private float fingerBendGain = 1.45f;      // Bù góc thiếu khi MediaPipe bị che đầu ngón
        [SerializeField] private float mcpRestOffsetDeg = 0f;       // Giảm về 0 để nắm đấm không bị hở
        [SerializeField] private float thumbCmcRestOffsetDeg = 10f; // Trừ nhẹ góc choãi tự nhiên của ngón cái
        [SerializeField] private float maxJointBendDeg = 115f;
        [SerializeField] private float fallbackFistBendDeg = 85f;

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
            if (_provider == null)
            {
                Debug.LogError("[Hand3DVisualizer] Chưa gắn UdpHandProvider!");
            }

            // Tự động đảm bảo tay trái uốn gập đúng chiều (-1 do xương đối xứng Blender) nếu chưa được đặt âm
            if (leftHandRig.fingerBendDirection > 0f)
            {
                leftHandRig.fingerBendDirection = -1f;
            }
            if (leftHandRig.thumbBendDirection > 0f)
            {
                leftHandRig.thumbBendDirection = -1f;
            }

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
                ApplyTestCurl(leftHandRig, debugTestCurl * 90f);
                ApplyTestCurl(rightHandRig, debugTestCurl * 90f);
                return;
            }

            if (_provider == null) return;

            _leftLungeOffset = Mathf.Lerp(_leftLungeOffset, 0f, Time.deltaTime * lungeReturnSpeed);
            _rightLungeOffset = Mathf.Lerp(_rightLungeOffset, 0f, Time.deltaTime * lungeReturnSpeed);

            UpdateHandVisual(_provider.LeftHand, leftHandRig, isLeft: true, _leftLungeOffset);
            UpdateHandVisual(_provider.RightHand, rightHandRig, isLeft: false, _rightLungeOffset);
        }

        private void ApplyTestCurl(HandRigConfig rig, float deg)
        {
            if (rig == null || rig.root == null) return;
            if (!rig.root.gameObject.activeSelf) rig.root.gameObject.SetActive(true);
            if (!rig.isInitialized) rig.CacheInitialRotations("Test");

            ApplyUniformAngle(rig.thumb, rig.thumbInitRot, deg * 0.65f, rig.thumbBendAxis, rig.thumbBendDirection);
            ApplyUniformAngle(rig.index, rig.indexInitRot, deg, rig.fingerBendAxis, rig.fingerBendDirection);
            ApplyUniformAngle(rig.middle, rig.middleInitRot, deg, rig.fingerBendAxis, rig.fingerBendDirection);
            ApplyUniformAngle(rig.ring, rig.ringInitRot, deg, rig.fingerBendAxis, rig.fingerBendDirection);
            ApplyUniformAngle(rig.pinky, rig.pinkyInitRot, deg, rig.fingerBendAxis, rig.fingerBendDirection);
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

            // 1. Di chuyển vị trí bàn tay trên mặt phẳng Hit Plane
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
                float targetAngle = data.shape == "Closed_Fist" ? fallbackFistBendDeg : 0f;
                ApplyUniformAngle(rig.thumb, rig.thumbInitRot, targetAngle * 0.65f, rig.thumbBendAxis, rig.thumbBendDirection);
                ApplyUniformAngle(rig.index, rig.indexInitRot, targetAngle, rig.fingerBendAxis, rig.fingerBendDirection);
                ApplyUniformAngle(rig.middle, rig.middleInitRot, targetAngle, rig.fingerBendAxis, rig.fingerBendDirection);
                ApplyUniformAngle(rig.ring, rig.ringInitRot, targetAngle, rig.fingerBendAxis, rig.fingerBendDirection);
                ApplyUniformAngle(rig.pinky, rig.pinkyInitRot, targetAngle, rig.fingerBendAxis, rig.fingerBendDirection);
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
                // Căn chỉnh pháp tuyến lòng bàn tay theo +Z và trục ngón tay theo +Y (khớp với bind pose gốc)
                Quaternion targetWorldRot = Quaternion.LookRotation(palmNormal, handForward)
                                            * Quaternion.Euler(rig.wristRotationOffset);
                rig.root.rotation = Quaternion.Slerp(rig.root.rotation, targetWorldRot, Time.deltaTime * rotationSmoothSpeed);
            }
        }

        public static Vector3 ToUnityHandSpace(Vector3 p)
        {
            // UdpHandProvider đã đảo trục Y; trục Z của MediaPipe cùng chiều +Z Unity nên giữ nguyên dấu
            return new Vector3(p.x, p.y, p.z);
        }

        public Vector3 MapNormalizedToWorld(float xUdp, float yUdp, float zOffset = 0f)
        {
            if (useCameraViewportMapping && Camera.main != null)
            {
                float depth = Mathf.Max(0.4f, hitPlaneZ + zOffset);
                return Camera.main.ViewportToWorldPoint(new Vector3(xUdp, yUdp, depth));
            }

            float worldX = (xUdp - 0.5f) * playWidth;
            float worldY = (yUdp - 0.5f) * playHeight + centerY;
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

            float a1 = CalcBendAngleDeg(p0, p1, p2, thumbCmcRestOffsetDeg);
            float a2 = CalcBendAngleDeg(p1, p2, p3, 5f);
            float a3 = CalcBendAngleDeg(p2, p3, p4, 3f);

            RotateBoneRelative(rig.thumb[0], rig.thumbInitRot[0], a1, rig.thumbBendAxis, rig.thumbBendDirection);
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

            float a1 = CalcBendAngleDeg(v0, v1, v2, mcpRestOffsetDeg);
            float a2 = CalcBendAngleDeg(v1, v2, v3, 2f);
            float a3 = CalcBendAngleDeg(v2, v3, v4, 2f);

            RotateBoneRelative(bones[0], initRots[0], a1, axis, dir);
            RotateBoneRelative(bones[1], initRots[1], a2, axis, dir);
            RotateBoneRelative(bones[2], initRots[2], a3, axis, dir);
        }

        private void ApplyUniformAngle(
            Transform[] bones, Quaternion[] initRots, float angleDeg, Vector3 axis, float dir)
        {
            if (bones == null) return;
            for (int i = 0; i < Mathf.Min(3, bones.Length); i++)
            {
                RotateBoneRelative(bones[i], initRots[i], angleDeg, axis, dir);
            }
        }

        private void RotateBoneRelative(
            Transform bone, Quaternion initRot, float angleDeg, Vector3 axis, float dir)
        {
            if (bone == null || axis.sqrMagnitude < 0.0001f) return;
            float clampedDir = Mathf.Sign(dir == 0f ? 1f : dir);
            Quaternion delta = Quaternion.AngleAxis(angleDeg * clampedDir, axis.normalized);
            Quaternion targetRot = initRot * delta;
            bone.localRotation = Quaternion.Slerp(bone.localRotation, targetRot, Time.deltaTime * jointSmoothSpeed);
        }

        private float CalcBendAngleDeg(Vector3 a, Vector3 b, Vector3 c, float restOffsetDeg)
        {
            Vector3 v1 = (a - b).normalized;
            Vector3 v2 = (c - b).normalized;
            float rawBend = 180f - Vector3.Angle(v1, v2);
            float adjusted = Mathf.Max(0f, rawBend - restOffsetDeg) * fingerBendGain;
            return Mathf.Clamp(adjusted, 0f, maxJointBendDeg);
        }

        [ContextMenu("Auto-Map Blender Bones (.L / .R)")]
        private void AutoMapBlenderBones()
        {
            // Tự động nhận diện hậu tố .L hoặc .R
            MapRigAutoSuffix(leftHandRig, ".L", ".R");
            MapRigAutoSuffix(rightHandRig, ".R", ".L");

            // Xương đối xứng qua trục X (Blender Symmetrize) có trục uốn gập cục bộ ngược chiều
            // nên tay trái cần direction = -1 để uốn gập vào lòng bàn tay
            leftHandRig.fingerBendDirection = -1f;
            leftHandRig.thumbBendDirection = -1f;
            rightHandRig.fingerBendDirection = 1f;
            rightHandRig.thumbBendDirection = 1f;

            Debug.Log("[Hand3DVisualizer] Đã tự động ánh xạ xong 30 đốt xương và cài đặt đúng chiều uốn (Left: -1, Right: 1).");
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