import argparse
import sys
from pathlib import Path

from kombu import Connection, Exchange, Queue
from mozlog import commandline

from git_hg_sync.application import Application
from git_hg_sync.config import Config
from git_hg_sync.pulse_worker import PulseWorker
from git_hg_sync.repo_synchronizer import RepoSynchronizer

HERE = Path(__file__).parent


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


def get_connection(config, ssl=True):
    return Connection(
        hostname=config.host,
        port=config.port,
        userid=config.userid,
        password=config.password,
        heartbeat=10,
        ssl=ssl,
    )


def get_queue(config):
    exchange = Exchange(config.exchange, type="topic")
    return Queue(
        name=config.queue,
        exchange=exchange,
        routing_key=config.routing_key,
        exclusive=False,
    )


def start_app(config, logger, *, one_shot=False):
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
        app = Application(worker, synchronizers, config.mappings)
        app.run()


def main() -> None:
    parser = get_parser()
    commandline.add_logging_group(parser)
    args = parser.parse_args()
    logger = commandline.setup_logging("service", args, {"raw": sys.stdout})
    config = Config.from_file(args.config)
    start_app(config, logger)


if __name__ == "__main__":
    main()
