using System.Collections.Concurrent;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

// [4] Receives JSON messages from Python on a background thread.
// Other scripts read them from Messages inside Update().
public class UdpReceiver : MonoBehaviour
{
    public int port = 5005;
    public ConcurrentQueue<string> Messages = new ConcurrentQueue<string>();

    UdpClient client;
    Thread thread;
    bool running;

    void Start()
    {
        client = new UdpClient(port);
        running = true;
        thread = new Thread(Listen) { IsBackground = true };
        thread.Start();
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
        }
    }

    void OnDestroy()
    {
        running = false;
        client?.Close();
    }
}
