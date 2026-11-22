using UnityEngine;

// The launcher: spawns one target every spawnIntervalMs on a random side (left/right lane)
// and flies it toward the camera. One target per interval, so targets never overlap.
public class TargetSpawner : MonoBehaviour
{
    [Header("Refs")]
    public StrikeJudge judge;
    [Tooltip("Target prefab (Duy, Assets/_Project/Targets/). Empty = use a plain cube.")]
    public GameObject targetPrefab;
    [Tooltip("Material for the fallback cube; tinted per kind.")]
    public Material targetMaterial;

    [Header("Rhythm")]
    public bool spawnOnStart = true;
    public int spawnIntervalMs = 1000;
    public float speed = 5f;            // world units per second

    [Header("Lanes (world space)")]
    public float spawnZ = 25f;
    public float laneX = 0.45f;         // left lane at -laneX, right lane at +laneX
    public float laneY = 1.3f;
    public float targetSize = 0.35f;

    [Header("Kinds to spawn")]
    public string[] kinds = { StrikeKinds.PunchStraight };
    public Color punchColor = new Color(1f, 0.55f, 0.1f);
    public Color blockColor = new Color(0.2f, 0.5f, 1f);
    public Color openPalmColor = new Color(0.2f, 0.85f, 0.35f);

    float nextSpawnTime;
    MaterialPropertyBlock block;
    static readonly int BaseColorId = Shader.PropertyToID("_BaseColor");

    public bool Running { get; set; }

    void Start()
    {
        Running = spawnOnStart;
        nextSpawnTime = Time.time + spawnIntervalMs / 1000f;
    }

    void Update()
    {
        if (!Running || Time.time < nextSpawnTime) return;
        nextSpawnTime += spawnIntervalMs / 1000f;
        Spawn(Random.value < 0.5f ? StrikeKinds.Left : StrikeKinds.Right,
              kinds.Length > 0 ? kinds[Random.Range(0, kinds.Length)] : StrikeKinds.PunchStraight);
    }

    public Target Spawn(string hand, string kind)
    {
        float x = hand == StrikeKinds.Left ? -laneX : laneX;
        var pos = new Vector3(x, laneY, spawnZ);

        GameObject go;
        if (targetPrefab != null)
        {
            go = Instantiate(targetPrefab, pos, Quaternion.identity, transform);
        }
        else
        {
            go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            Destroy(go.GetComponent<Collider>());   // hit check does not use physics
            go.transform.SetParent(transform, false);
            go.transform.position = pos;
            go.transform.localScale = Vector3.one * targetSize;
            var r = go.GetComponent<Renderer>();
            if (targetMaterial != null) r.sharedMaterial = targetMaterial;
            block ??= new MaterialPropertyBlock();
            block.SetColor(BaseColorId, ColorFor(kind));
            r.SetPropertyBlock(block);
        }
        go.name = $"Target_{hand}_{kind}";

        if (!go.TryGetComponent(out Target t)) t = go.AddComponent<Target>();
        t.Init(hand, kind, speed, judge != null ? judge.hitZoneNearZ : 0f, judge);
        return t;
    }

    Color ColorFor(string kind) => kind switch
    {
        StrikeKinds.Block => blockColor,
        StrikeKinds.OpenPalm => openPalmColor,
        _ => punchColor,
    };
}
