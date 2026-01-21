from msight_edge.nodes import RTSPSourceNode
import argparse

def main():
    parser = argparse.ArgumentParser(
        description='Launch a source node to grap rtsp stream.')
    parser.add_argument('-n', '--name', required=True,
                        type=str, help='The name of the source node.')
    parser.add_argument('-t', '--publish-topic', required=True,
                        type=str, help='The topic to publish the image data to.')
    parser.add_argument('--sensor-name', type=str,
                        required=True, help='The name of the sensor.')
    parser.add_argument('-u', '--url', required=True, help="The url of the RTSP stream")
    parser.add_argument('-g', '--gap', type = int, default = 0, help="gap between the two frames published")
    # resize_ratio
    parser.add_argument('-r', '--resize-ratio', type=float,
                        help='The ratio to resize the image. Default is 1.0.')
    parser.add_argument('--rtsp-transport', type=str, default="tcp", choices=["tcp", "udp"],
                        help='The RTSP transport protocol, "tcp" or "udp". Default is "tcp".')
    args = parser.parse_args()

    # print("hhh" + args.sensor_name)
    source_node = RTSPSourceNode.create(
        args.name, args.publish_topic, args.sensor_name, args.url, rtsp_transport=args.rtsp_transport, gap=args.gap, resize_ratio=args.resize_ratio)
    print(f"Starting the RTSP Source node {source_node.name}.")
    print(f"Publishing to topic {source_node.publish_topic_name}, publish data {source_node.publish_topic_data_type}, heartbeat tolerance: {source_node.heartbeat_tolerance}.")
    # source_node.spin()


if __name__ == "__main__":
    main()