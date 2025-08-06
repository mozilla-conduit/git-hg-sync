import argparse
import sys
from pathlib import Path

import sentry_sdk
from kombu import Connection, Exchange, Queue
from mozlog import commandline
from pydantic import ValidationError

from git_hg_sync.application import Application
from git_hg_sync.config import Config, PulseConfig
from git_hg_sync.pulse_worker import PulseWorker
from git_hg_sync.repo_synchronizer import RepoSynchronizer


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        required=True,
        help="Configuration file path.",
    )
    return parser


def get_connection(config: PulseConfig) -> Connection:
    return Connection(
        hostname=config.host,
        port=config.port,
        userid=config.userid,
        password=config.password,
        heartbeat=config.heartbeat,
        ssl=config.ssl,
    )


def get_queue(config: Config | PulseConfig) -> Queue:
    exchange = Exchange(config.exchange, type="topic")
    return Queue(
        name=config.queue,
        exchange=exchange,
        routing_key=config.routing_key,
        exclusive=False,
    )


def start_app(
    config: Config, logger: commandline.StructuredLogger, *, one_shot: bool = False
) -> None:
    pulse_config = config.pulse
    connection = get_connection(pulse_config)

    queue = get_queue(pulse_config)

    queue(connection).queue_declare()
    queue(connection).queue_bind()
    logger.info(f"Reading messages from {connection}/{queue.name} ...")

    synchronizers = {
        tracked_repo.url: RepoSynchronizer(
            config.clones.directory / tracked_repo.name, tracked_repo.url
        )
        for tracked_repo in config.tracked_repositories
    }
    with connection as conn:
        conn.connect()
        logger.info(f"connected to {conn.host}")
        worker = PulseWorker(conn, queue, one_shot=one_shot)
        app = Application(
            worker, synchronizers, [*config.branch_mappings, *config.tag_mappings]
        )
        app.run()


def main() -> None:
    parser = get_parser()
    commandline.add_logging_group(parser)
    args = parser.parse_args()
    logger = commandline.setup_logging("service", args)
    try:
        config = Config.from_file(args.config)
    except ValidationError as e:
        logger.error(f"Invalid configuration: {e}")
        sys.exit(1)

    sentry_config = config.sentry
    if sentry_config and sentry_config.sentry_dsn:
        logger.info(f"Sentry DSN: {sentry_config.sentry_dsn}")
        sentry_sdk.init(sentry_config.sentry_dsn, max_value_length=4096)
    start_app(config, logger)


if __name__ == "__main__":
    main()
