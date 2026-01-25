import socketserver

from msight_core.nodes import NodeConfig, ServerSourceNode
from msight_core.data import BytesData


class CommandServerSourceNode(ServerSourceNode):
    """A UDP server source node that receives external command messages and publishes them as BytesData."""

    default_configs = NodeConfig(
        publish_topic_data_type=BytesData,
        heartbeat_tolerance=-1, # Disable heartbeat for server nodes
    )

    def __init__(self, config, host, port):
        super().__init__(config)
        self.server = None
        self._host = host
        self._port = port

    # -----------------------------
    # 1) initialize(): setup server
    # -----------------------------
    def initialize(self):
        """Initialize UDP server resources."""

        node = self  # capture for the handler

        class _UDPHandler(socketserver.BaseRequestHandler):
            def handle(self):
                # BaseRequestHandler for UDP: request = (data, socket)
                data, _sock = self.request
                client = self.client_address

                # Wire raw bytes into the MSight node
                node.handle_incoming(data)

        # ReusableUDPServer avoids "address already in use" for rapid restarts
        class _ReusableUDPServer(socketserver.ThreadingUDPServer):
            allow_reuse_address = True

        self.server = _ReusableUDPServer((self._host, self._port), _UDPHandler)
        self.logger.info(f"UDP server initialized on {self._host}:{self._port}")

    # -----------------------------
    # 2) serve(): run server loop
    # -----------------------------
    def serve(self):
        """Run the UDP server loop (blocking)."""
        if self.server is None:
            raise RuntimeError("Server is not initialized. Call initialize() first.")

        self.logger.info("UDP server is now serving (waiting for external commands)...")
        self.server.serve_forever(poll_interval=0.2)

    def on_message(self, raw_bytes: bytes):
        """Translate raw bytes into MSight data and publish."""
        if not raw_bytes:
            return

        # Publish as BytesData into MSight graph
        payload = BytesData(
            data=raw_bytes,
            sensor_name=self.sensor_name,
        )

        self.logger.info(
            f"Published command bytes: {payload.data} to topic: {self.publish_topic.name}"
        )

        return payload


if __name__ == "__main__":
    # Note: host/port are optional here; include them if your NodeConfig supports custom fields.
    config = NodeConfig(
        publish_topic_name="command_topic",
        name="CommandServerSourceNode",
        sensor_name="CommandServerSourceSensor",
    )
    HOST, PORT = "localhost", 9999
    node = CommandServerSourceNode(config, HOST, PORT)
    node.spin()