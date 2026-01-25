from msight_core.data import SensorData
from dataclasses import dataclass, field

@dataclass
class TrafficLightCommandData(SensorData):
    command: str = field(default="")  # Command to change traffic light state
    traffic_state: str = field(default="none")  # Current state of the traffic light

    def get_traffic_state(self) -> str:
        """Get the current traffic light state."""
        return self.traffic_state.upper().strip()
