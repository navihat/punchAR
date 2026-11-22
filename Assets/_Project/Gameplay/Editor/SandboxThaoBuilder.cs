using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

// Menu "punchAR > Build Sandbox_Thao Scene": builds Assets/Scenes/Sandbox_Thao.unity from code
// (track, launcher, left/right hit zones, gameplay objects, keyboard + UDP strikes).
// Re-run any time to rebuild the scene from scratch; materials are kept and updated.
public static class SandboxThaoBuilder
{
    const string ScenePath = "Assets/Scenes/Sandbox_Thao.unity";
    const string MatFolder = "Assets/_Project/Gameplay/Materials";

    [MenuItem("punchAR/Build Sandbox_Thao Scene")]
    public static void Build()
    {
        if (System.IO.File.Exists(ScenePath) &&
            !EditorUtility.DisplayDialog("Sandbox_Thao", $"{ScenePath} already exists. Rebuild it from scratch?", "Rebuild", "Cancel"))
            return;
        if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;

        var scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);

        // ---- Materials ----
        var matTrack = Mat("Track", new Color(0.18f, 0.18f, 0.2f));
        var matLine = Mat("LaneLine", new Color(0.9f, 0.9f, 0.9f));
        var matLauncher = Mat("Launcher", new Color(0.35f, 0.35f, 0.4f));
        var matZoneLeft = Mat("HitZoneLeft", new Color(0.2f, 0.6f, 1f, 0.35f), transparent: true);
        var matZoneRight = Mat("HitZoneRight", new Color(1f, 0.3f, 0.3f, 0.35f), transparent: true);
        var matTarget = Mat("Target", Color.white);

        // ---- Gameplay components first, layout reads their numbers ----
        var gameplay = new GameObject("Gameplay");
        var score = gameplay.AddComponent<ScoreKeeper>();
        var judge = gameplay.AddComponent<StrikeJudge>();
        judge.score = score;
        var hud = gameplay.AddComponent<GameplayDebugHud>();
        hud.score = score;
        hud.judge = judge;

        var spawnerGo = new GameObject("TargetSpawner");
        spawnerGo.transform.SetParent(gameplay.transform, false);
        var spawner = spawnerGo.AddComponent<TargetSpawner>();
        spawner.judge = judge;
        spawner.targetMaterial = matTarget;

        var receiverGo = new GameObject("UdpReceiver");
        var receiver = receiverGo.AddComponent<UdpReceiver>();

        var gm = new GameObject("GameManager").AddComponent<GameManager>();
        gm.receiver = receiver;
        gm.judge = judge;

        // ---- Camera: player's eyes at the origin, looking down the track (+Z) ----
        var cam = Camera.main;
        cam.transform.SetPositionAndRotation(new Vector3(0f, 1.4f, 0f), Quaternion.Euler(8f, 0f, 0f));
        cam.fieldOfView = 60f;
        cam.nearClipPlane = 0.1f;

        // ---- Environment ----
        var env = new GameObject("Environment").transform;
        float len = spawner.spawnZ + 5f;

        Box("Track", env, new Vector3(0f, -0.05f, len / 2f), new Vector3(2.4f, 0.1f, len), matTrack);
        Box("CenterLine", env, new Vector3(0f, 0.005f, len / 2f), new Vector3(0.03f, 0.01f, len), matLine);
        Box("EdgeLeft", env, new Vector3(-1.2f, 0.005f, len / 2f), new Vector3(0.03f, 0.01f, len), matLine);
        Box("EdgeRight", env, new Vector3(1.2f, 0.005f, len / 2f), new Vector3(0.03f, 0.01f, len), matLine);

        // Launcher at the far end, one barrel per lane
        Box("Launcher", env, new Vector3(0f, spawner.laneY, spawner.spawnZ + 0.9f), new Vector3(1.8f, 1.2f, 1f), matLauncher);
        foreach (var side in new[] { -1f, 1f })
        {
            // Cylinder is 2 units tall along Y; rotated 90° on X it points down the track.
            var barrel = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            barrel.name = side < 0 ? "Barrel_Left" : "Barrel_Right";
            barrel.transform.SetParent(env, false);
            barrel.transform.SetPositionAndRotation(new Vector3(side * spawner.laneX, spawner.laneY, spawner.spawnZ + 0.2f), Quaternion.Euler(90f, 0f, 0f));
            barrel.transform.localScale = new Vector3(0.4f, 0.3f, 0.4f);
            barrel.GetComponent<Renderer>().sharedMaterial = matLine;
        }

        // Hit zones: a translucent box per lane between hitZoneNearZ and hitZoneFarZ
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
        Debug.Log($"[SandboxThaoBuilder] Built {ScenePath}. Press Play, then F/J when a cube is inside a hit zone.");
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

    // Creates or updates a URP Lit material asset in MatFolder.
    static Material Mat(string name, Color color, bool transparent = false)
    {
        if (!AssetDatabase.IsValidFolder(MatFolder))
            AssetDatabase.CreateFolder("Assets/_Project/Gameplay", "Materials");

        string path = $"{MatFolder}/{name}.mat";
        var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (mat == null)
        {
            mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
            AssetDatabase.CreateAsset(mat, path);
        }
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
