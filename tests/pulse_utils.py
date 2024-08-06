import sys
from datetime import datetime
from pathlib import Path

import kombu

from git_hg_sync.config import Config

HERE = Path(__file__).parent


def send_pulse_message(pulse_config, payload, ssl=True):
    """Send a pulse message
    The routing key will be constructed from the repository URL.
    The Pulse message will be constructed from the specified payload
    and sent to the requested exchange.
    """
    userid = pulse_config.userid
    password = pulse_config.password
    routing_key = pulse_config.routing_key
    host = pulse_config.host
    port = pulse_config.port
    exchange = pulse_config.exchange
    queue = pulse_config.queue
    print(f"connecting to pulse at {host}:{port} as {userid}")

    connection = kombu.Connection(
        hostname=host,
        port=port,
        userid=userid,
        password=password,
        connect_timeout=100,
        ssl=ssl,
    )
    connection.connect()

    with connection:
        ex = kombu.Exchange(exchange, type="direct")
        queue = kombu.Queue(
            name=queue,
            exchange=exchange,
            routing_key=routing_key,
            durable=True,
            exclusive=False,
            auto_delete=False,
        )
        queue(connection).declare()

        producer = connection.Producer(
            exchange=ex, routing_key=routing_key, serializer="json"
        )

        data = {
            "payload": payload,
            "_meta": {
                "exchange": exchange,
                "routing_key": routing_key,
                "serializer": "json",
                "sent": datetime.now(),
            },
        }

        print(f"publishing message to {exchange}")
        producer.publish(data)


if __name__ == "__main__":
    config = Config.from_file(HERE.parent / "config.toml")
    config.mappings
    message_type = sys.argv[1]
    match message_type:
        case "push":
            payload = {
                "type": "push",
                "repo_url": sys.argv[2],
                "branches": {sys.argv[3]: sys.argv[4]},
                "time": 0,
                "pushid": 0,
                "user": "user",
                "push_json_url": "push_json_url",
            }
        case "tag":
            payload = {
                "type": "tag",
                "repo_url": "/home/fbessou/dev/MOZI/fake-forge/git/chatzilla",
                "tag": "tag",
                "commit": "88949ac3ad633e92cf52354d91857074e264ad12",
                "time": 0,
                "pushid": 0,
                "user": "user",
                "push_json_url": "push_json_url",
            }
        case _:
            raise NotImplementedError()
    print(payload)
    send_pulse_message(config.pulse, payload)
