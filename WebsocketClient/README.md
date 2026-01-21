# MSight WebSocket Client Node Tutorial 

In this tutorial, we will demonstrate how to use the **MSight WebSocket client node** to receive data from a WebSocket server, wrap the received payload into `BytesData`, and publish it into the MSight system.

We will:

1. Start a **dummy WebSocket server** that periodically pushes text messages to any connected client.
2. Launch the **MSight WebSocket client node** to connect to this server and publish the received data to a topic.
3. Use a **Bytes Viewer node** to subscribe to the topic and verify that the messages are indeed received.

> *Figure: Overall setup*
> (WebSocket Server) → (MSight WebSocket Client Node) → (MSight Pub/Sub Topic) → (Bytes Viewer Node)

---

## 🧰 Prerequisites

* **MSight** installed (edge toolkit).
* **Redis** server running and configured for MSight. You can run Redis using Docker:

  ```bash
  docker run -d --name redis -p 6379:6379 redis:latest
  ```

  Or install it locally by following the instructions here: [this link](xxxx)
* **Python ****************`websockets`**************** module** installed. Install it with:

```bash
pip install websockets
```

Also, if you're not sure how to set `MSIGHT_EDGE_DEVICE_NAME`, you can simply set it to `testing` for this tutorial:

```bash
export MSIGHT_EDGE_DEVICE_NAME=testing
```

Make sure your `MSIGHT_EDGE_DEVICE_NAME` and other basic MSight environment settings are already configured and that `msight_status` works correctly.

---

## 🖥️ Step 1: Set Up a Testing WebSocket Server

First, we create a simple WebSocket server in Python that sends a dummy message every 2 seconds to any connected client.

Save the following script as, for example, `ws_server.py`:

```python
import asyncio
import datetime
import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

HOST = "0.0.0.0"
PORT = 8765
INTERVAL_SECONDS = 2


async def handle_client(websocket):
    """
    Called for each new client connection.
    Periodically sends a dummy message to this client until it disconnects.
    """
    client = websocket.remote_address
    print(f"[+] Client connected: {client}")

    try:
        while True:
            now = datetime.datetime.now().isoformat(timespec="seconds")
            message = f"dummy message at {now}"
            await websocket.send(message)
            print(f"  -> sent to {client}: {message}")
            await asyncio.sleep(INTERVAL_SECONDS)

    except (ConnectionClosedOK, ConnectionClosedError):
        print(f"[-] Client disconnected: {client}")

    except Exception as e:
        print(f"[!] Error with client {client}: {e}")


async def main():
    print(f"Starting WebSocket server at ws://{HOST}:{PORT}")

    async with websockets.serve(
        handle_client,
        HOST,
        PORT,
        ping_interval=None  # optional: disable ping
    ):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
```

Then start the WebSocket server:

```bash
python ws_server.py
```

You should see logs in the terminal once clients connect.

---

## 🔌 Step 2: Launch the MSight WebSocket Client Node

Next, we start the MSight WebSocket client node, which will:

* Connect to the WebSocket server at `ws://localhost:8765`.
* Wrap each received message into `BytesData`.
* Publish those messages to the MSight topic `websocket_topic`.

Run the following command:

```bash
msight_launch_websocket_client \
  -n websocket_node \
  -t websocket_topic \
  -u ws://localhost:8765 \
  --sensor-name websocket_sensor \
  -g 0
```

### Command Explanation

* `-n websocket_node`
  Sets the **node name** to `websocket_node`. This is how the node will appear in MSight status and logs.

* `-t websocket_topic`
  The **publish topic**. All received WebSocket messages (wrapped as `BytesData`) will be published to this topic.

* `-u ws://localhost:8765`
  The **WebSocket server URL** to connect to. Here we use the test server we just started.

* `--sensor-name websocket_sensor`
  A human-readable **sensor name** associated with this data source in the MSight system.

* `-g 0`
  The **gap** parameter. `gap` controls the minimum interval (in seconds) between published messages for this node.

  * `-g 0` means **no throttling**: every received message is published.
  * Larger values (e.g., `-g 9`) mean the node will publish **1 out of every (g+1) messages**. For example, `-g 9` means **publish every 10th message**.

Once this node starts, it will connect to the WebSocket server and begin publishing the incoming dummy messages as `BytesData` into `websocket_topic`.

---

## 🧪 Step 3: Verify Reception with the Bytes Viewer Node

Finally, we use the **Bytes Viewer node** to subscribe to the same topic and print the received data.

Run:

```bash
msight_launch_bytes_viewer -t websocket_topic
```

The Bytes Viewer node will subscribe to `websocket_topic` and print out the received `BytesData` content. You should see output corresponding to the dummy messages sent by the WebSocket server, for example:

```text
[websocket_topic] dummy message at 2025-11-17T01:23:45
[websocket_topic] dummy message at 2025-11-17T01:23:47
...
```

If you see these messages, it confirms that:

1. The WebSocket server is sending messages.
2. The MSight WebSocket client node is receiving and publishing them as `BytesData`.
3. The Bytes Viewer node is successfully subscribing and printing the data.

---

## 🎉 Conclusion

In this tutorial, we:

* Set up a simple WebSocket server that periodically pushes dummy messages to connected clients.
* Used the **MSight WebSocket client node** to connect to this server, wrap messages into `BytesData`, and publish them into the MSight ecosystem.
* Verified the data flow using the **Bytes Viewer node**.

You can now adapt this setup to connect to real WebSocket data sources (e.g., telemetry feeds, external services) and integrate them into your MSight-based pipelines.
