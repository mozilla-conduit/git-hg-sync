import argparse
import logging
from pathlib import Path

import sentry_sdk
from kombu import Connection, Exchange, Queue
from mozlog import commandline

from git_hg_sync.application import Application
from git_hg_sync.config import Config, PulseConfig
from git_hg_sync.pulse_worker import PulseWorker
from git_hg_sync.repo_synchronizer import RepoSynchronizer


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        required=True,
        help="Configuration file path.",
    )
    return parser


def get_connection(config: PulseConfig):
    return Connection(
        hostname=config.host,
        port=config.port,
        userid=config.userid,
        password=config.password,
        heartbeat=10,
        ssl=config.ssl,
    )


def get_queue(config):
    exchange = Exchange(config.exchange, type="topic")
    return Queue(
        name=config.queue,
        exchange=exchange,
        routing_key=config.routing_key,
        exclusive=False,
    )


def start_app(
    config: Config, logger: logging.Logger, *, one_shot: bool = False
) -> None:
    pulse_config = config.pulse
    connection = get_connection(pulse_config)

    queue = get_queue(pulse_config)

    synchronizers = {
        tracked_repo.url: RepoSynchronizer(
            config.clones.directory / tracked_repo.name, tracked_repo.url
        )
        for tracked_repo in config.tracked_repositories
    }
    with connection as conn:
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
    config = Config.from_file(args.config)

    sentry_config = config.sentry
    if sentry_config and sentry_config.sentry_url:
        logger.info(f"sentry url: {sentry_config.sentry_url}")
        sentry_sdk.init(sentry_config.sentry_url)
    start_app(config, logger)


if __name__ == "__main__":
    main()
