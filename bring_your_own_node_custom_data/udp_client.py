import socket


def main(host="127.0.0.1", port=9999):
    server_addr = (host, port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print(f"UDP client ready. Target server: {host}:{port}")
    print("Type 'n' + Enter to send NEXT_PHASE. Type 'q' + Enter to quit.")

    while True:
        cmd = input("> ").strip().lower()
        if cmd == "q":
            break
        if cmd == "n":
            payload = b"NEXT_PHASE"
            sock.sendto(payload, server_addr)
            print(f"Sent: {payload!r} -> {server_addr}")
        else:
            print("Unknown input. Use 'n' to send, 'q' to quit.")

    sock.close()


if __name__ == "__main__":
    main()
