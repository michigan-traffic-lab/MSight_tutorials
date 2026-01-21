# custom_http_server.py
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import base64
from pathlib import Path

receiving_folder = Path("received_images/")
receiving_folder.mkdir(exist_ok=True)
class MyHandler(BaseHTTPRequestHandler):
    counter = 0
    def do_GET(self):
        message = "Hello, this is a simple Python HTTP server!"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(message)))
        self.end_headers()
        self.wfile.write(message.encode("utf-8"))

    def do_POST(self):
        # Read body
        content_length = int(self.headers.get("Content-Length", 0))
        partition_key = self.headers.get("X-Partition-Key")
        body = self.rfile.read(content_length)

        print("Received POST body:", len(body), "bytes")
        if partition_key:
            print("Partition Key:", partition_key)

        # Build response
        response = {"status_code": "ok", "text": f"Server received {len(body)} bytes, partition key {partition_key}"}
        response_bytes = json.dumps(response).encode("utf-8")

        # Send headers
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()

        # Send body
        self.wfile.write(response_bytes)
        ## parse the body and get image
        payload = json.loads(body.decode("utf-8"))
        base64_image = payload.get("image")
        if base64_image:
            image_data = base64.b64decode(base64_image)
            with open(receiving_folder / f"received_image_{MyHandler.counter}.jpg", "wb") as f:
                f.write(image_data)
            print("Image saved as received_image.jpg")
            MyHandler.counter += 1

HOST = "0.0.0.0"
PORT = 8080

if __name__ == "__main__":
    httpd = HTTPServer((HOST, PORT), MyHandler)
    print(f"Running on {HOST}:{PORT}")
    httpd.serve_forever()
