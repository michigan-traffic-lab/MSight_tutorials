from msight_core.nodes import DataProcessingNode, NodeConfig
from msight_core.data import BytesData

class CommandProcessNode(DataProcessingNode):
    default_configs = NodeConfig(
        publish_topic_data_type=BytesData,
    )
    def __init__(self, config):
        super().__init__(config)
        self.current_state = 0
        self.traffic_light_states = ["RED", "GREEN", "YELLOW"]

    def process(self, data):
        """
        This is the main function to override to process incoming data.
        In this example, we interpret the command message and update the traffic light state accordingly.
        """
        command = data.data.decode('utf-8')
        self.logger.info(f"Received command message: {command} from topic: {self.subscribe_topic.name}")

        if command == "NEXT_PHASE":
            self.current_state = (self.current_state + 1) % len(self.traffic_light_states)
            new_state = self.traffic_light_states[self.current_state]
            self.logger.info(f"Transitioning to new traffic light state: {new_state}")
            data.data = new_state.encode('utf-8')
            return data

            
        else:
            self.logger.warning(f"Unknown command received: {command}")
            return None

if __name__ == "__main__":
    config = NodeConfig(
        subscribe_topic_name="command_topic",
        publish_topic_name="traffic_light_state_topic",
        name="CommandProcessNode",
    )
    node = CommandProcessNode(config)
    node.spin()
