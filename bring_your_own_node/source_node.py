from msight_core.nodes import SourceNode, NodeConfig
from msight_core.data import BytesData
import time


class CommandSourceNode(SourceNode):
    """A source node that generates command messages as bytes data.

    Args:
        SourceNode (SourceNode): The base source node class.
    """

    default_configs = NodeConfig(
        publish_topic_data_type=BytesData,
    )

    def __init__(self, config):
        super().__init__(config)
    
    def get_data(self):
        """
        This is the main function to override to generate data.
        In this example, we generate a simple command message as BytesData and wait for 2 seconds between messages.
        """
        command_message = b"NEXT_PHASE"
        time.sleep(2)
        self.logger.info(f"Generated command message: {command_message}, sending to topic: {self.publish_topic.name}")
        return BytesData(
            data=command_message,
            sensor_name=self.sensor_name,
        )
    
if __name__ == "__main__":
    config = NodeConfig(
        publish_topic_name="command_topic",
        name="CommandSourceNode",
        sensor_name="CommandSourceSensor",
    )
    node = CommandSourceNode(config)
    node.spin()
