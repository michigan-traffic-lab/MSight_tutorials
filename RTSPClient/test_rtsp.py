import av
import time

# >>> CHANGE THIS IF NEEDED <<<
# If you run this on the host and RTSP server is from docker-compose, use localhost:
RTSP_URL = "rtsp://localhost:8554/live.stream"
# If you run this inside another container on the same network:
# RTSP_URL = "rtsp://rtsp-server:8554/live.stream"


def main():
    print(f"Opening RTSP stream: {RTSP_URL}")

    # Open the container with RTSP options
    container = av.open(
        RTSP_URL,
        options={
            "rtsp_transport": "udp",  # or "udp" to test difference
            "max_delay": "0",
        },
    )

    video_stream = container.streams.video[0]

    print("Stream opened. Decoding frames...")
    last_ts = None
    start_time = time.time()
    frame_count = 0

    try:
        for frame in container.decode(video_stream):
            now = time.time()
            if last_ts is not None:
                dt = now - last_ts
                print(f"Frame {frame_count:04d} | Δt = {dt:.3f}s")
            else:
                print(f"Frame {frame_count:04d} | first frame")

            last_ts = now
            frame_count += 1

            # Stop after some frames so it doesn't run forever
            if frame_count >= 300:
                break

    except KeyboardInterrupt:
        print("Interrupted by user.")

    total_time = time.time() - start_time
    if frame_count > 1:
        print(
            f"\nReceived {frame_count} frames in {total_time:.2f}s "
            f"(~{frame_count / total_time:.2f} fps)"
        )
    else:
        print("No frames received or only one frame received.")

    container.close()
    print("Done.")


if __name__ == "__main__":
    main()
