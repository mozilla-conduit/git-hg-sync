import logging
import os
from dataclasses import dataclass

from kombu import Connection, Exchange, Queue

from git_hg_sync import config

logger = logging.getLogger()
pulse_conf = config.get_config()["pulse"]


@dataclass
class Push:
    type: str
    repo_url: str
    heads: list[str]
    commits: list[str]
    time: int
    pushid: int
    user: str
    push_json_url: str


@dataclass
class Tag:
    type: str
    repo_url: str
    tag: str
    commits: str
    time: int
    pushid: int
    user: str
    push_json_url: str


def callback(body, message):
    print("Received message: %s" % body)
    payload = body["payload"]
    if payload["type"] == "push":
        push = Push(**payload)
        logger.info(push)
    elif payload["type"] == "tag":
        tag = Tag(**payload)
        logger.debug(tag)
    else:
        raise Exception(f"unsupported type message {payload['type']}")
    message.ack()


def get_connection():
    return Connection(
        hostname=pulse_conf["host"],
        port=pulse_conf["port"],
        userid=pulse_conf["userid"],
        password=os.environ["PULSE_PASSWORD"],
        ssl=True,
    )


def get_consumer(connection):
    exchange = pulse_conf["exchange"]
    exchange = Exchange(exchange, type="topic")
    exchange(connection).declare(passive=True)  # raise an error if exchange doesn't exist

    queue = Queue(
        name=pulse_conf["queue"],
        exchange=exchange,
        routing_key=pulse_conf["routing_key"],
        durable=True,
        exclusive=False,
        auto_delete=False,
    )

    consumer = connection.Consumer(queue, auto_declare=False, callbacks=[callback])
    consumer.queues[0].queue_declare()
    consumer.queues[0].queue_bind()
    return consumer


def drain():
    with get_connection() as connection:
        with get_consumer(connection) as consumer:
            while True:
                try:
                    connection.drain_events(timeout=1)
                except TimeoutError:
                    count = consumer.queues[0].queue_declare().message_count
                    if count < 100:
                        break


if __name__ == "__main__":
    drain()
