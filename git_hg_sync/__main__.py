import argparse
import sys
from pathlib import Path

from kombu import Connection, Exchange, Queue
from mozlog import commandline

from git_hg_sync import config
from git_hg_sync.pulse_consumer import Worker
from git_hg_sync.repo_synchronizer import RepoSynchronyzer

HERE = Path(__file__).parent


def get_parser():
    parser = argparse.ArgumentParser()
    return parser


def get_connection(config):
    return Connection(
        hostname=config["host"],
        port=config["port"],
        userid=config["userid"],
        password=config["password"],
        heartbeat=10,
        ssl=True,
    )


def get_queue(config):
    exchange = Exchange(config["exchange"], type="topic")
    return Queue(
        name=config["queue"],
        exchange=exchange,
        routing_key=config["routing_key"],
        exclusive=False,
    )


def main():
    parser = get_parser()
    commandline.add_logging_group(parser)
    args = parser.parse_args()
    logger = commandline.setup_logging("service", args, {"raw": sys.stdout})
    pulse_config = config.get_pulse_config(HERE.parent / "config.ini")["pulse"]
    connection = get_connection(pulse_config)

    repos_config = config.get_repos_config(HERE.parent / "repos.json")

    queue = get_queue(pulse_config)
    repo_synchronyzer = RepoSynchronyzer(repos_config=repos_config)
    with connection as conn:
        logger.info(f"connected to {conn.host}")
        worker = Worker(conn, queue, repo_synchronyzer=repo_synchronyzer)
        worker.run()


if __name__ == "__main__":
    main()
