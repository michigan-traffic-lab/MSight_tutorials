# MSight Tutorial: Building and Testing a UDP Server Node

This short tutorial walks you through setting up a **UDP Source Node** in MSight, sending bytes via a simple UDP client, and verifying that the messages are correctly published and received within the MSight system.

## 📦 Prerequisites

Before beginning, ensure the following are installed:

- **MSight** system installed
- **Docker** (for running Redis)

MSight uses Redis as its pub/sub backend, so we need to start a Redis server before launching any nodes.

## 🚀 Step 1: Start Redis Using Docker

Run the following Docker command:

```bash
docker run -d --name msight-redis -p 6379:6379 redis
```

This launches Redis in a container and exposes it on port **6379** (default).

Verify it's running:

```bash
docker ps
```

You should see `msight-redis` in the list.

## 🚀 Step 2: Launch the MSight UDP Server Node

Now start a UDP server node that listens on port **5000** and publishes received bytes to the topic `udp_topic`.

```bash
msight_launch_udp_server \
    -n udp_server_node \
    -t udp_topic \
    --sensor-name test_udp \
    --port 5000
```

Expected output:

```
2025-11-15 02:16:56,498 - local - udp_server_node - INFO :: Received data of size 22, publishing to udp_topic.
```

## 🧪 Step 3: Write a Test UDP Client (Python)

Create a file named **test_udp_client.py**:

```python
import socket
import time

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000
MESSAGE = b"hello from test client"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

while True:
    try:
        print(f"Sending: {MESSAGE!r} to {SERVER_HOST}:{SERVER_PORT}")
        sock.sendto(MESSAGE, (SERVER_HOST, SERVER_PORT))
        time.sleep(1)
    except KeyboardInterrupt:
        sock.close()
```

Run it:

```bash
python test_udp_client.py
```

## 👀 Step 4: Launch a Bytes Viewer Node (Subscriber)

```bash
msight_launch_bytes_viewer \
    -n bytes_viewer \
    -t udp_topic \
    --filter-sensor-name test_udp
```

Output example:

```
2025-11-15 02:18:12,144 - local - bytes_viewer - INFO :: Bytes received, latency:  4 ms, sensor_name: test_udp
2025-11-15 02:18:12,144 - local - bytes_viewer - INFO :: Payload: b'hello from test client'
```

## 🎉 Congratulations!

You have successfully completed the MSight UDP server tutorial!
