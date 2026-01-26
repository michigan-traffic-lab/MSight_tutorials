## This is a sample script to consume records from an AWS Kinesis Data Stream.
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