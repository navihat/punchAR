using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
using PunchAR.Hand3D;

// Menu "punchAR > Build Sandbox_Duy Scene": builds Assets/Scenes/Sandbox_Duy.unity from code
// Combines HandTrackingRig (Duy) + Gameplay & Lanes (Thao) + Single UdpReceiver (Port 5005).
public static class SandboxDuyBuilder
{
    const string ScenePath = "Assets/Scenes/Sandbox_Duy.unity";
    const string MatFolder = "Assets/_Project/Gameplay/Materials";
    const string RigPrefabPath = "Assets/_Project/Hands/Prefabs/HandTrackingRig.prefab";

    [MenuItem("punchAR/Build Sandbox_Duy Scene")]
    public static void Build()
    {
        if (File.Exists(ScenePath) && !Application.isBatchMode &&
            !EditorUtility.DisplayDialog("Sandbox_Duy", $"{ScenePath} already exists. Rebuild it from scratch?", "Rebuild", "Cancel"))
            return;

        if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;

        var scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);

        // ---- 1. Materials ----
        var matTrack = Mat("Track", new Color(0.18f, 0.18f, 0.2f));
        var matLine = Mat("LaneLine", new Color(0.9f, 0.9f, 0.9f));
        var matLauncher = Mat("Launcher", new Color(0.35f, 0.35f, 0.4f));
        var matZoneLeft = Mat("HitZoneLeft", new Color(0.2f, 0.6f, 1f, 0.35f), transparent: true);
        var matZoneRight = Mat("HitZoneRight", new Color(1f, 0.3f, 0.3f, 0.35f), transparent: true);
        var matTarget = Mat("Target", Color.white);

        // ---- 2. Gameplay Components ----
        var gameplay = new GameObject("Gameplay");
        var score = gameplay.AddComponent<ScoreKeeper>();
        var judge = gameplay.AddComponent<StrikeJudge>();
        judge.score = score;
        judge.hitZoneNearZ = 1.5f;
        judge.hitZoneFarZ = 3.0f;

        var hud = gameplay.AddComponent<GameplayDebugHud>();
        hud.score = score;
        hud.judge = judge;

        var spawnerGo = new GameObject("TargetSpawner");
        spawnerGo.transform.SetParent(gameplay.transform, false);
        var spawner = spawnerGo.AddComponent<TargetSpawner>();
        spawner.judge = judge;
        spawner.targetMaterial = matTarget;
        spawner.laneX = 0.45f;
        spawner.laneY = 1.30f;
        spawner.spawnZ = 25f;

        // ---- 3. Single UdpReceiver (Port 5005) ----
        var receiverGo = new GameObject("UdpReceiver");
        var receiver = receiverGo.AddComponent<UdpReceiver>();
        receiver.port = 5005;

        // ---- 4. GameManager ----
        var gm = new GameObject("GameManager").AddComponent<GameManager>();
        gm.receiver = receiver;
        gm.judge = judge;
        gm.keyboardStrikes = true;

        // ---- 5. HandTrackingRig Prefab Instance ----
        var rigPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(RigPrefabPath);
        if (rigPrefab != null)
        {
            var rigGo = (GameObject)PrefabUtility.InstantiatePrefab(rigPrefab, scene);
            rigGo.name = "HandTrackingRig";
            rigGo.transform.position = Vector3.zero;
            rigGo.transform.rotation = Quaternion.identity;

            var provider = rigGo.GetComponent<UdpHandProvider>();
            if (provider != null)
            {
                var soProvider = new SerializedObject(provider);
                var propReceiver = soProvider.FindProperty("udpReceiver");
                if (propReceiver != null)
                {
                    propReceiver.objectReferenceValue = receiver;
                    soProvider.ApplyModifiedProperties();
                }
            }

            var vis = rigGo.GetComponent<Hand3DVisualizer>();
            if (vis != null)
            {
                var soVis = new SerializedObject(vis);
                soVis.FindProperty("useCameraViewportMapping").boolValue = false;
                soVis.FindProperty("playWidth").floatValue = 1.8f;
                soVis.FindProperty("playHeight").floatValue = 1.2f;
                soVis.FindProperty("centerY").floatValue = 1.3f;
                soVis.FindProperty("hitPlaneZ").floatValue = 2.0f;
                soVis.FindProperty("enableManualCurlTest").boolValue = false;
                soVis.FindProperty("hideHandsWhenLost").boolValue = true;
                soVis.ApplyModifiedProperties();
                vis.AutoMapBlenderBones();
            }
        }
        else
        {
            Debug.LogError($"[SandboxDuyBuilder] Không tìm thấy Rig Prefab tại {RigPrefabPath}!");
        }

        // ---- 6. Camera ----
        var cam = Camera.main;
        if (cam != null)
        {
            cam.transform.SetPositionAndRotation(new Vector3(0f, 1.4f, 0f), Quaternion.Euler(8f, 0f, 0f));
            cam.fieldOfView = 60f;
            cam.nearClipPlane = 0.1f;
        }

        // ---- 7. Environment ----
        var env = new GameObject("Environment").transform;
        float len = spawner.spawnZ + 5f;

        Box("Track", env, new Vector3(0f, -0.05f, len / 2f), new Vector3(2.4f, 0.1f, len), matTrack);
        Box("CenterLine", env, new Vector3(0f, 0.005f, len / 2f), new Vector3(0.03f, 0.01f, len), matLine);
        Box("EdgeLeft", env, new Vector3(-1.2f, 0.005f, len / 2f), new Vector3(0.03f, 0.01f, len), matLine);
        Box("EdgeRight", env, new Vector3(1.2f, 0.005f, len / 2f), new Vector3(0.03f, 0.01f, len), matLine);

        // Launcher at the far end
        Box("Launcher", env, new Vector3(0f, spawner.laneY, spawner.spawnZ + 0.9f), new Vector3(1.8f, 1.2f, 1f), matLauncher);
        foreach (var side in new[] { -1f, 1f })
        {
            var barrel = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            barrel.name = side < 0 ? "Barrel_Left" : "Barrel_Right";
            barrel.transform.SetParent(env, false);
            barrel.transform.SetPositionAndRotation(new Vector3(side * spawner.laneX, spawner.laneY, spawner.spawnZ + 0.2f), Quaternion.Euler(90f, 0f, 0f));
            barrel.transform.localScale = new Vector3(0.4f, 0.3f, 0.4f);
            barrel.GetComponent<Renderer>().sharedMaterial = matLine;
        }

        // Hit zones
        float zoneDepth = judge.hitZoneFarZ - judge.hitZoneNearZ;
        float zoneZ = (judge.hitZoneFarZ + judge.hitZoneNearZ) / 2f;
        var zones = new GameObject("HitZones").transform;
        zones.SetParent(env, false);
        Box("HitZone_Left", zones, new Vector3(-spawner.laneX, spawner.laneY, zoneZ), new Vector3(0.8f, 0.8f, zoneDepth), matZoneLeft);
        Box("HitZone_Right", zones, new Vector3(spawner.laneX, spawner.laneY, zoneZ), new Vector3(0.8f, 0.8f, zoneDepth), matZoneRight);

        foreach (var c in env.GetComponentsInChildren<Collider>()) Object.DestroyImmediate(c);

        EditorSceneManager.MarkSceneDirty(scene);
        EditorSceneManager.SaveScene(scene, ScenePath);
        AssetDatabase.SaveAssets();
        Debug.Log($"[SandboxDuyBuilder] Đã dựng thành công {ScenePath}. HandTrackingRig + Gameplay sẵn sàng.");
    }

    static GameObject Box(string name, Transform parent, Vector3 pos, Vector3 scale, Material mat)
    {
        var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
        go.name = name;
        go.transform.SetParent(parent, false);
        go.transform.position = pos;
        go.transform.localScale = scale;
        go.GetComponent<Renderer>().sharedMaterial = mat;
        return go;
    }

    static Material Mat(string name, Color color, bool transparent = false)
    {
        string path = $"{MatFolder}/{name}.mat";
        var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (mat != null)
        {
            // Tận dụng Material đã có của Thảo ở chế độ CHỈ ĐỌC, tuyệt đối không dirty hay sửa file của Thảo
            return mat;
        }

        if (!AssetDatabase.IsValidFolder(MatFolder))
            AssetDatabase.CreateFolder("Assets/_Project/Gameplay", "Materials");

        mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
        AssetDatabase.CreateAsset(mat, path);
        mat.SetColor("_BaseColor", color);

        if (transparent)
        {
            mat.SetFloat("_Surface", 1f);
            mat.SetFloat("_Blend", 0f);
            mat.SetOverrideTag("RenderType", "Transparent");
            mat.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha);
            mat.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
            mat.SetFloat("_SrcBlendAlpha", (float)BlendMode.One);
            mat.SetFloat("_DstBlendAlpha", (float)BlendMode.OneMinusSrcAlpha);
            mat.SetFloat("_ZWrite", 0f);
            mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            mat.renderQueue = (int)RenderQueue.Transparent;
        }
        EditorUtility.SetDirty(mat);
        return mat;
    }
}
