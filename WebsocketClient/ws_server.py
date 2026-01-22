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
