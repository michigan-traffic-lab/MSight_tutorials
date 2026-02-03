# Tutorial: Pushing Sensor Data to Cloud through AWS Kinesis

This tutorial demonstrates how to set up a **simple RTSP-based sensor streaming pipeline** in MSight and stream the data to the cloud using **Amazon Kinesis Data Streams**. This architecture is the **recommended approach for real-time sensor streaming with low end-to-end latency**, making it suitable for applications such as live perception, online analytics, and time-critical safety services.

In this setup, sensor data are ingested from RTSP sources at the edge, serialized by MSight, and pushed directly to AWS Kinesis for immediate downstream consumption. While this design provides near–real-time performance, it is important to note that continuous real-time streaming can be **costly at scale**. If your application does not require sub-second latency and is primarily focused on cost efficiency, consider the alternative tutorial that aggregates image data locally and uploads encoded video segments to the cloud for offline or near–real-time processing.

## Prerequisites

The prerequisites for this tutorial are largely the same as those in the S3 video uploading example, with one important addition: cloud-side Kinesis configuration.

### 1. MSight Installation

MSight must be installed and properly configured on the edge device. This tutorial assumes that MSight nodes can be launched from the command line and that Redis-based pub/sub is available.

### 2. Docker

Docker is required to run the RTSP server used in this tutorial. If Docker is not yet installed, follow the official installation guide:

* [Docker installation guide](https://docs.docker.com/get-docker/)

Verify the installation:

```bash
docker --version
```

### 3. Redis (Message Broker)

MSight uses Redis as the internal message broker. You can start a Redis instance using Docker:

```bash
docker run -d \
  --name msight-redis \
  -p 6379:6379 \
  redis:7
```

### 4. AWS Kinesis Cloud Setup

Before streaming data to the cloud, you must configure AWS Kinesis resources, including the data stream, IAM permissions, and credentials. Follow the step-by-step guide below to complete the minimal cloud-side setup:

* `../../cloud-integration/min-setup-kinesis.md`

This guide walks through creating a Kinesis Data Stream, configuring IAM policies, and preparing the AWS credentials required by MSight.

### 5. AWS Credentials Configuration (Edge Device)

After completing the cloud setup, configure AWS credentials on the edge device so that MSight can authenticate with AWS:

```bash
aws configure
```

Provide your access key, secret key, default region, and output format when prompted.

## Setup an RTSP Server

For this tutorial, we use a lightweight, fully containerized RTSP setup based on Docker Compose. This setup includes two services:

* An **RTSP server** powered by MediaMTX (formerly rtsp-simple-server)
* A **video source container** that continuously streams a local `.mp4` file to the RTSP server using FFmpeg

This approach allows you to reproduce a stable RTSP stream without relying on physical cameras, which is ideal for development, testing, and documentation purposes.

### Docker Compose Configuration

Create a file named `docker-compose.yml` in an empty directory and place a sample video file (for example, `sample.mp4`) in the same directory. Then add the following content:

```yaml
version: "3.9"

services:
  rtsp-server:
    image: bluenviron/mediamtx:latest
    container_name: rtsp-server
    restart: unless-stopped
    ports:
      - "8554:8554"        # RTSP
    environment:
      MTX_PROTOCOLS: "udp,tcp"   # allow both

  video-source:
    image: jrottenberg/ffmpeg:4.4-alpine
    container_name: rtsp-video-source
    restart: unless-stopped
    depends_on:
      - rtsp-server
    volumes:
      - .:/data:ro    # sample.mp4 is here
    # ffmpeg is the entrypoint; we only pass args:
    command: >
      -re -stream_loop -1
      -loglevel info
      -fflags nobuffer
      -flags low_delay
      -i /data/sample.mp4
      -an
      -c:v libx264
      -preset veryfast
      -tune zerolatency
      -pix_fmt yuv420p
      -profile:v baseline
      -g 24 -keyint_min 24 -sc_threshold 0
      -f rtsp
      -rtsp_transport udp
      rtsp://rtsp-server:8554/live.stream
```

### Launch the RTSP Server

From the directory containing `docker-compose.yml` and `sample.mp4`, start the RTSP services with:

```bash
docker compose up -d
```

Once the containers are running, an RTSP stream will be continuously available at:

```
rtsp://localhost:8554/live.stream
```

This RTSP endpoint will be consumed by the MSight source node in the next step.

## Start the RTSP Source Node

With the RTSP server running, launch an MSight **source node** that connects to the RTSP stream and publishes decoded image frames into the MSight pub/sub system.

Run the following command on the edge device:

```bash
msight_launch_rtsp \
  -n rtsp_node \
  -pt rtsp_topic \
  --sensor-name rtsp_sensor \
  -u rtsp://localhost:8554/live.stream \
  -g 3 \
  --rtsp-transport tcp
```

### Parameter Explanation

* `-n rtsp_node`: Assigns a unique name to this MSight node instance.
* `-pt rtsp_topic`: Specifies the MSight topic to which decoded image frames will be published.
* `--sensor-name rtsp_sensor`: Logical sensor identifier used internally by MSight for data provenance and downstream processing.
* `-u rtsp://localhost:8554/live.stream`: RTSP stream URL provided by the MediaMTX server.
* `-g 3`: Gap (in frames) between published messages. Setting this to 3 subsamples the data rate to approximately 1/4, which helps manage throughput to Kinesis. Continuous streaming of high-frame-rate RTSP can quickly exceed a single shard's capacity. In production, you can increase the number of shards in your Kinesis stream configuration instead of subsampling.
* `--rtsp-transport tcp`: Forces TCP-based RTSP transport.

Once started, this node continuously pulls frames from the RTSP stream, decodes them, and publishes image data to the `rtsp_topic`. These frames will be streamed directly to AWS Kinesis in the subsequent steps without local aggregation.

## Start the Kinesis Pusher Node

The final step is to launch the MSight **Kinesis pusher node**, which subscribes to the RTSP image topic and pushes each serialized sensor message directly into an Amazon Kinesis Data Stream.

> Replace `SOME_STREAM_NAME` with the name of your Kinesis stream created during the cloud setup step.

Run the following command on the edge device:

```bash
msight_launch_kinesis_pusher \
  --name kinesis-pusher \
  -st rtsp_topic \
  --partition-key-mode sensor_name \
  --stream-name SOME_STREAM_NAME \
  --shards 2
```

### Parameter Explanation

* `--name kinesis-pusher`: Assigns a unique name to the Kinesis pusher node.
* `-st rtsp_topic`: Source topic to subscribe to (raw frames from the RTSP source node).
* `--stream-name SOME_STREAM_NAME`: Target Kinesis Data Stream name.
* `--partition-key-mode`: Controls how Kinesis partition keys are chosen. Supported modes are:

  * `sensor_name`: Use a deterministic partition-key scheme derived from the MSight sensor name.
  * `random`: Use a random partition key per record.
* `--shards 2`: **Only used when** `--partition-key-mode sensor_name` is selected.

### Partition Key Mode and Shard Usage

Kinesis uses the **partition key** to determine which shard a record is routed to. In MSight, `--partition-key-mode` and `--shards` work together to control how records are distributed.

* When `--partition-key-mode sensor_name` is used, you must also specify `--shards N`. This `N` tells the pusher how many distinct partition keys it will rotate through for the same sensor. For example, if one shard cannot handle the throughput of a high-rate RTSP stream, you can set `--shards 2` to alternate between two partition keys, which encourages Kinesis to distribute records across (up to) two shards.

  * Important tradeoff: when rotating across multiple partition keys, **record ordering is not guaranteed** across shards.
  * Note: the `--shards` value here is **not** the same as the total number of shards configured for the Kinesis stream. The stream may have many more shards; `--shards` only specifies how many shards (via partition keys) this particular pusher intends to utilize.

* When `--partition-key-mode random` is used, the pusher chooses a random partition key per record, and `--shards` is not used.

At this point, the end-to-end real-time streaming pipeline is complete: RTSP frames are ingested at the edge and pushed to Kinesis for immediate downstream consumption (e.g., Lambda, Kinesis Data Analytics, or custom consumers).

If you see **sequence numbers** printed in the pusher node’s console logs, that is a healthy signal: the sequence number is returned by **Kinesis on the cloud side**, confirming that records are being accepted and persisted in the stream.

## Troubleshooting: Firehose Dynamic Partitioning Errors

If you see an error on the AWS side similar to:

* `DynamicPartitioning.MetadataExtractionFailed`
* `partitionKeys values must not be null or empty`

and your MSight edge pusher prints **successful Kinesis sequence numbers**, this usually indicates the issue is **not with Kinesis Data Streams ingestion**, but with **Kinesis Data Firehose** (or another downstream consumer) that is reading from the Kinesis stream.

### Why this happens

* The **Kinesis partition key** you set in `msight_launch_kinesis_pusher` is only used by **Kinesis Data Streams** to route records to shards.
* **Firehose dynamic partitioning** is a separate feature. When enabled, Firehose expects to extract **partition keys from the record payload** using its configured *Metadata extraction* rules (typically JQ expressions) and then uses those keys to build an S3 prefix (or other destination partition paths).
* If the payload is **not JSON**, or the configured extraction expression does not match your payload schema, Firehose will extract `null`/empty partition keys and produce the `MetadataExtractionFailed` error.

In MSight, the record payload is often a **binary serialization** (e.g., msgpack / bytes) rather than plain JSON. In that case, Firehose cannot directly extract dynamic partition keys unless you add a transformation layer.

## Consume the Kinesis Stream (Simple Python Example)

Below is a minimal Python script that reads records from a Kinesis Data Stream and prints basic metadata. This is useful for validating end-to-end connectivity and ensuring data are arriving in the stream.

> Prerequisites:
>
> * Python 3.9+
> * `pip install boto3`
> * AWS credentials configured (e.g., via `aws configure`) with permission to read from the stream.

Create a file named `consume_kinesis.py`:

```python
import argparse
import time
from typing import Optional

import boto3


def get_first_shard_id(kinesis, stream_name: str) -> str:
    """Return the first shard id from the stream description."""
    resp = kinesis.describe_stream_summary(StreamName=stream_name)
    # For a small tutorial stream, listing shards directly is simplest.
    shards = kinesis.list_shards(StreamName=stream_name)["Shards"]
    if not shards:
        raise RuntimeError(f"No shards found in stream: {stream_name}")
    return shards[0]["ShardId"]


def get_shard_iterator(
    kinesis,
    stream_name: str,
    shard_id: str,
    iterator_type: str,
    sequence_number: Optional[str] = None,
):
    kwargs = {
        "StreamName": stream_name,
        "ShardId": shard_id,
        "ShardIteratorType": iterator_type,
    }
    if iterator_type == "AT_SEQUENCE_NUMBER" and sequence_number:
        kwargs["StartingSequenceNumber"] = sequence_number
    return kinesis.get_shard_iterator(**kwargs)["ShardIterator"]


def main():
    parser = argparse.ArgumentParser(description="Consume records from an AWS Kinesis Data Stream")
    parser.add_argument("--stream-name", required=True, help="Kinesis stream name")
    parser.add_argument(
        "--iterator",
        default="LATEST",
        choices=["LATEST", "TRIM_HORIZON"],
        help="Where to start reading: LATEST (new records) or TRIM_HORIZON (from oldest)",
    )
    parser.add_argument("--poll-interval", type=float, default=0.5, help="Seconds between polls when empty")
    parser.add_argument("--region", default=None, help="AWS region override (optional)")
    args = parser.parse_args()

    kinesis = boto3.client("kinesis", region_name=args.region)

    shard_id = get_first_shard_id(kinesis, args.stream_name)
    shard_iterator = get_shard_iterator(kinesis, args.stream_name, shard_id, args.iterator)

    print(f"Consuming stream={args.stream_name}, shard={shard_id}, iterator={args.iterator}")

    while True:
        resp = kinesis.get_records(ShardIterator=shard_iterator, Limit=100)
        shard_iterator = resp.get("NextShardIterator")

        records = resp.get("Records", [])
        if not records:
            time.sleep(args.poll_interval)
            continue

        for r in records:
            seq = r.get("SequenceNumber")
            pk = r.get("PartitionKey")
            data = r.get("Data")  # bytes
            print(f"SequenceNumber={seq} PartitionKey={pk} Bytes={len(data)}")

        # Throttle politely; Kinesis has API rate limits.
        time.sleep(args.poll_interval)


if __name__ == "__main__":
    main()
```

Run it as:

```bash
python consume_kinesis.py --stream-name SOME_STREAM_NAME --iterator LATEST
```

Notes:

* This example reads from **one shard** for simplicity. In production (or when you use multiple partition keys), a complete consumer should read from **all shards** (or use the Kinesis Client Library / enhanced fan-out).
* The record payload (`Data`) is a raw byte array produced by MSight serialization. Decoding it depends on your MSight message schema and serialization format.
* You can use this script on the cloud side to consume records in real time for cloud real-time analytics or processing.
* Kinesis is polling based; for lower latency, consider using using AWS SNS to consume records and trigger subsequent processing.

