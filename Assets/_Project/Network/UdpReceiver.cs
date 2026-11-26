using System;
using System.Collections.Concurrent;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

// [4] Receives JSON messages from Python on a background thread.
// Dispatches messages via events to all subscribers on the main thread.
public class UdpReceiver : MonoBehaviour
{
    public int port = 5005;
    public ConcurrentQueue<string> Messages = new ConcurrentQueue<string>();

    public event Action<PoseMessage> OnPoseReceived;
    public event Action<StrikeMessage> OnStrikeReceived;
    public event Action<HandLostMessage> OnHandLostReceived;

    UdpClient client;
    Thread thread;
    bool running;

    void Start()
    {
        try
        {
            client = new UdpClient(port);
            running = true;
            thread = new Thread(Listen) { IsBackground = true };
            thread.Start();
            Debug.Log($"[UdpReceiver] Listening on port {port}...");
        }
        catch (Exception ex)
        {
            Debug.LogError($"[UdpReceiver] Failed to bind port {port}: {ex.Message}");
        }
    }

    void Update()
    {
        while (Messages.TryDequeue(out string json))
        {
            var baseMsg = JsonUtility.FromJson<BaseMessage>(json);
            if (baseMsg == null || string.IsNullOrEmpty(baseMsg.type)) continue;

            switch (baseMsg.type)
            {
                case "pose":
                    var pose = JsonUtility.FromJson<PoseMessage>(json);
                    OnPoseReceived?.Invoke(pose);
                    break;
                case "strike":
                    var strike = JsonUtility.FromJson<StrikeMessage>(json);
                    OnStrikeReceived?.Invoke(strike);
                    break;
                case "hand_lost":
                    var lost = JsonUtility.FromJson<HandLostMessage>(json);
                    OnHandLostReceived?.Invoke(lost);
                    break;
            }
        }
    }

    void Listen()
    {
        var remote = new IPEndPoint(IPAddress.Any, 0);
        while (running)
        {
            try
            {
                byte[] data = client.Receive(ref remote);
                Messages.Enqueue(Encoding.UTF8.GetString(data));
            }
            catch (SocketException) { }
            catch (ObjectDisposedException) { break; }
        }
    }

    void OnDestroy()
    {
        running = false;
        client?.Close();
    }
}
