#!/usr/bin/env python

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from kombu.simple import SimpleQueue
from mozlog import commandline
from pydantic import ValidationError

from git_hg_sync.__main__ import get_connection
from git_hg_sync.config import Config
from git_hg_sync.pulse_worker import PulseWorker


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    environment = os.getenv("ENVIRONMENT")
    env_config = f"config-{environment}.toml"
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        required=False,
        default=Path(env_config),
        help="Configuration file path.",
    )
    parser.add_argument(
        "-r",
        "--repository-url",
        type=str,
        required=True,
        help="URL of the repository for which to delete a message",
    )
    parser.add_argument(
        "-p",
        "--push-id",
        type=int,
        required=True,
        help="ID of the Push to delete",
    )
    return parser


def remove_push_message(
    queue: SimpleQueue,
    logger: commandline.StructuredLogger,
    repository_url: str,
    push_id: int,
) -> int:
    # Receive a message
    message = queue.get(block=True, timeout=5)
    if not message:
        logger.info("No message received")
        return 0

    body = message.payload
    payload = body.get("payload")
    if not payload:
        logger.warning(f"No payload in {message}, rejecting")
        message.reject()
        return 0

    try:
        push = PulseWorker.parse_entity(payload)
    except:
        logger.warning(f"Cannot parse message {message}, rejecting")
        message.reject()
        raise

    if push.repo_url != repository_url or push.push_id != push_id:
        logger.warning(f"Message not matching deletion criteria: {message}, rejecting")
        message.reject()
        return 0

    print(f"{message.payload}")

    # Acknowledge the message
    message.ack()

    return 1


def main() -> None:
    parser = get_parser()
    args = parser.parse_args()
    logger = commandline.setup_logging("service", args)

    logger.info(f"Using configuration file {args.config}")
    try:
        config = Config.from_file(args.config)
    except ValidationError as e:
        logger.error(f"Invalid configuration: {e}")
        sys.exit(1)

    pulse_config = config.pulse
    connection = get_connection(pulse_config)
    queue = connection.SimpleQueue(
        pulse_config.queue,
        # exchange_opts={"name": pulse_config.exchange, "type": "topic"},
    )

    logger.info(
        f"Removing push message {args.push_id} for repository {args.repository_url} ..."
    )
    try:
        count = remove_push_message(queue, logger, args.repository_url, args.push_id)
    except Exception as e:
        logger.error(f"Error removing message from queue: {e.__class__}, {e}")
        sys.exit(1)
    else:
        logger.info(f"Removed {count} message for {args.repository_url}")
    finally:
        queue.close()


if __name__ == "__main__":
    main()
