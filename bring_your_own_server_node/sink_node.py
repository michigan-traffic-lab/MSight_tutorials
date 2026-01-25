from msight_core.nodes import SinkNode, NodeConfig


class ConsoleTrafficLightUI:
    """A tiny, dependency-free console UI for rendering traffic light states."""

    # ANSI color codes (works in most modern terminals)
    _RESET = "\033[0m"
    _DIM = "\033[2m"
    _BOLD = "\033[1m"
    _RED = "\033[31m"
    _YELLOW = "\033[33m"
    _GREEN = "\033[32m"

    def __init__(self, enable_ansi=True):
        self.enable_ansi = enable_ansi
        self._printed_once = False

    def set_state(self, state):
        """Render the current traffic light state to the console."""
        state = (state or "").strip().upper()
        if state not in ("RED", "YELLOW", "GREEN"):
            state = "OFF"

        # Decide which lamp is active
        active = {"RED": state == "RED", "YELLOW": state == "YELLOW", "GREEN": state == "GREEN"}

        def lamp(on, color_code):
            if not self.enable_ansi:
                return "●" if on else "○"
            return f"{color_code}{self._BOLD}●{self._RESET}" if on else f"{self._DIM}○{self._RESET}"

        red = lamp(active["RED"], self._RED)
        yellow = lamp(active["YELLOW"], self._YELLOW)
        green = lamp(active["GREEN"], self._GREEN)

        header = f"Traffic Light State: {state}"
        body = f"\n  {red}\n  {yellow}\n  {green}\n"

        # Clear previously printed block (simple in-place refresh)
        if self.enable_ansi and self._printed_once:
            # Move cursor up 5 lines (1 header + 3 lamps + trailing blank) and clear to end
            print("\033[5F\033[J", end="")

        print(header + body, end="")
        self._printed_once = True


class TrafficLightSinkNode(SinkNode):
    """A sink node that receives traffic light state messages and displays them."""

    def __init__(self, config, ui=None):
        super().__init__(config)
        self.ui = ui or ConsoleTrafficLightUI()

    def on_message(self, data):
        """Handle incoming data and update the UI."""
        traffic_light_state = data.data.decode("utf-8")
        traffic_light_state = traffic_light_state.strip().upper()

        self.logger.info(
            f"Received traffic light state: {traffic_light_state} from topic: {self.subscribe_topic.name}"
        )

        # Minimal, clear sink-node behavior: render the latest state
        self.ui.set_state(traffic_light_state)


if __name__ == "__main__":
    config = NodeConfig(
        subscribe_topic_name="traffic_light_state_topic",
        name="TrafficLightSinkNode",
    )
    node = TrafficLightSinkNode(config)
    node.spin()