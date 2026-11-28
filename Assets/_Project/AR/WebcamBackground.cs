using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using UnityEngine;
using UnityEngine.UI;
using Debug = UnityEngine.Debug;

// AR background: shows the webcam image sent by Python (python/punchar/transport/frame_sender.py).
// Packet = 12-byte header (little-endian int32 frame, int64 t) + JPEG. Same frame/t as the "pose" message.
// The image is already mirrored by Python: shown as is, so pose x, y (0..1 viewport) line up with it.
//
// Setup: add this component to any GameObject in the scene and press Play. It creates its own canvas;
// no scene/prefab edits needed.
//   BottomLeft / BottomRight: small window on top of the game, in that corner.
//   FullScreen: background behind all 3D objects (AR); pose x, y line up with the image only in this mode.
public class WebcamBackground : MonoBehaviour
{
    public enum Layout { BottomRight, BottomLeft, FullScreen }

    [SerializeField] int port = 5006;
    [SerializeField] Layout layout = Layout.BottomRight;
    [Tooltip("Window width as a fraction of the screen width (corner layouts)")]
    [Range(0.1f, 0.6f)] [SerializeField] float windowWidth = 0.25f;
    [Tooltip("Gap between the window and the screen edges, in pixels (corner layouts)")]
    [SerializeField] float margin = 16f;
    [Tooltip("Camera that renders the game (FullScreen layout). Empty = Camera.main")]
    [SerializeField] Camera targetCamera;
    [Tooltip("Brightness of the image (1 = original, lower = dimmer)")]
    [Range(0f, 1f)] [SerializeField] float brightness = 1f;
    [Tooltip("Log p50/p95 of latency and decode time to the Console every N seconds (0 = off)")]
    [SerializeField] float statsEverySeconds = 5f;

    public int LastFrame { get; private set; } = -1;
    public long LastLatencyMs { get; private set; }   // Unity time at upload - t (capture time)
    public double LastDecodeMs { get; private set; }

    UdpClient client;
    Thread thread;
    volatile bool running;
    readonly object gate = new object();
    byte[] latest;       // newest packet from the network thread; older ones are dropped
    int receivedCount;

    Texture2D tex;
    Canvas canvas;
    RawImage image;
    readonly List<float> latencySamples = new List<float>();
    readonly List<float> decodeSamples = new List<float>();
    int shownCount, droppedCount;
    float statsTimer;

    void Start()
    {
        tex = new Texture2D(2, 2, TextureFormat.RGB24, false);
        CreateCanvas();
        try
        {
            client = new UdpClient(port);
            client.Client.ReceiveBufferSize = 1 << 20;
            running = true;
            thread = new Thread(Listen) { IsBackground = true };
            thread.Start();
            Debug.Log($"[WebcamBackground] Listening on port {port}...");
        }
        catch (Exception ex)
        {
            Debug.LogError($"[WebcamBackground] Failed to bind port {port}: {ex.Message}");
        }
    }

    void CreateCanvas()
    {
        var canvasGo = new GameObject("WebcamCanvas");
        canvasGo.transform.SetParent(transform, false);
        canvas = canvasGo.AddComponent<Canvas>();

        var imageGo = new GameObject("WebcamImage");
        imageGo.transform.SetParent(canvasGo.transform, false);
        image = imageGo.AddComponent<RawImage>();
        image.texture = tex;
        image.raycastTarget = false;
        ApplyLayout();
    }

    // Re-applied every frame so Inspector changes (layout, size) take effect while playing.
    void ApplyLayout()
    {
        var rt = image.rectTransform;
        if (layout == Layout.FullScreen)
        {
            Camera cam = targetCamera != null ? targetCamera : Camera.main;
            if (cam != null)
            {
                canvas.renderMode = RenderMode.ScreenSpaceCamera;
                canvas.worldCamera = cam;
                canvas.planeDistance = cam.farClipPlane * 0.95f;  // behind every 3D object
            }
            else
            {
                canvas.renderMode = RenderMode.ScreenSpaceOverlay;  // no camera: covers the scene
            }
            canvas.sortingOrder = -1000;
            rt.anchorMin = Vector2.zero;   // stretch to the full screen, same area as viewport 0..1
            rt.anchorMax = Vector2.one;
            rt.pivot = new Vector2(0.5f, 0.5f);
            rt.offsetMin = Vector2.zero;
            rt.offsetMax = Vector2.zero;
            return;
        }

        canvas.renderMode = RenderMode.ScreenSpaceOverlay;   // small window drawn on top of the game
        canvas.sortingOrder = 100;
        float side = layout == Layout.BottomLeft ? 0f : 1f;
        rt.anchorMin = rt.anchorMax = rt.pivot = new Vector2(side, 0f);
        float w = Screen.width * windowWidth;
        float aspect = tex.width > 2 ? (float)tex.height / tex.width : 9f / 16f;  // before the first frame: 16:9
        rt.sizeDelta = new Vector2(w, w * aspect);
        rt.anchoredPosition = new Vector2(layout == Layout.BottomLeft ? margin : -margin, margin);
    }

    void Listen()
    {
        var remote = new IPEndPoint(IPAddress.Any, 0);
        while (running)
        {
            try
            {
                byte[] data = client.Receive(ref remote);
                lock (gate)
                {
                    latest = data;
                    receivedCount++;
                }
            }
            catch (SocketException) { }
            catch (ObjectDisposedException) { break; }
        }
    }

    void Update()
    {
        byte[] packet;
        int received;
        lock (gate)
        {
            packet = latest;
            latest = null;
            received = receivedCount;
            receivedCount = 0;
        }
        if (packet != null && packet.Length > 12) ShowPacket(packet, received);

        ApplyLayout();
        image.color = new Color(brightness, brightness, brightness, 1f);
        LogStats();
    }

    void ShowPacket(byte[] packet, int received)
    {
        int frame = BitConverter.ToInt32(packet, 0);
        long t = BitConverter.ToInt64(packet, 4);
        var jpeg = new byte[packet.Length - 12];
        Buffer.BlockCopy(packet, 12, jpeg, 0, jpeg.Length);

        var sw = Stopwatch.StartNew();
        if (!tex.LoadImage(jpeg)) return;   // decodes and uploads to the GPU (main thread)
        LastDecodeMs = sw.Elapsed.TotalMilliseconds;

        LastFrame = frame;
        LastLatencyMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() - t;
        latencySamples.Add(LastLatencyMs);
        decodeSamples.Add((float)LastDecodeMs);
        shownCount++;
        droppedCount += received - 1;   // packets that arrived within one Unity frame: only the last is shown
    }

    void LogStats()
    {
        if (statsEverySeconds <= 0f) return;
        statsTimer += Time.unscaledDeltaTime;
        if (statsTimer < statsEverySeconds || latencySamples.Count == 0) return;

        Debug.Log($"[WebcamBackground] {shownCount / statsTimer:F1} fps shown, {droppedCount} dropped | " +
                  $"latency (now - t) p50 {Percentile(latencySamples, 0.5f):F0} / p95 {Percentile(latencySamples, 0.95f):F0} ms | " +
                  $"decode p50 {Percentile(decodeSamples, 0.5f):F1} / p95 {Percentile(decodeSamples, 0.95f):F1} ms | " +
                  $"{tex.width}x{tex.height}");
        latencySamples.Clear();
        decodeSamples.Clear();
        shownCount = droppedCount = 0;
        statsTimer = 0f;
    }

    static float Percentile(List<float> values, float p)
    {
        values.Sort();
        return values[Mathf.Clamp(Mathf.CeilToInt(p * values.Count) - 1, 0, values.Count - 1)];
    }

    void OnDestroy()
    {
        running = false;
        client?.Close();
        if (tex != null) Destroy(tex);
    }
}
