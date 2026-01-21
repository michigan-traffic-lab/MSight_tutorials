# test_udp_client.py
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