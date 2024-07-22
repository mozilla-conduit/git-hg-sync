import logging
from pathlib import Path

from kombu import Connection, Exchange, Queue

from git_hg_sync import config
from git_hg_sync.pulse_consumer import Worker

HERE = Path(__file__).parent


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
    logging.basicConfig(level=logging.INFO)
    pulse_config = config.get_pulse_config(HERE.parent / "config.ini")["pulse"]
    connection = get_connection(pulse_config)
    queue = get_queue(pulse_config)
    with connection as conn:
        worker = Worker(conn, queue)
        worker.run()


if __name__ == "__main__":
    main()
