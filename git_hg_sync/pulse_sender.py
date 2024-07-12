import logging
import os
from datetime import datetime

import kombu

from git_hg_sync import config


logger = logging.getLogger()


def send_pulse_message(payload, queue=None):
    """Send a pulse message
    The routing key will be constructed from the repository URL.
    The Pulse message will be constructed from the specified payload
    and sent to the requested exchange.
    if queue is not None, create queue
    """
    pulse_conf = config.get_config()["pulse"]
    userid = pulse_conf["userid"]
    password = os.environ["PULSE_PASSWORD"]
    routing_key = pulse_conf["routing_key"]
    host = pulse_conf["host"]
    port = pulse_conf["port"]
    exchange = pulse_conf["exchange"]

    print(f"connecting to pulse at {host}:{port} as {userid}")

    connection = kombu.Connection(
        hostname=host,
        port=port,
        userid=userid,
        password=password,
        connect_timeout=100,
        ssl=True,
    )
    connection.connect()

    with connection:
        ex = kombu.Exchange(exchange, type="direct")
        if queue:
            queue = kombu.Queue(
                name=queue,
                exchange=exchange,
                routing_key=routing_key,
                durable=True,
                exclusive=False,
                auto_delete=False,
            )
            queue(connection).declare()

        producer = connection.Producer(exchange=ex, routing_key=routing_key, serializer="json")

        data = {
            "payload": payload,
            "_meta": {
                "exchange": exchange,
                "routing_key": routing_key,
                "serializer": "json",
                "sent": datetime.utcnow().isoformat(),
            },
        }

        logger.info("publishing message to %s#%s" % (exchange, routing_key))
        logger.debug("payload: %s" % payload)
        producer.publish(data)


if __name__ == "__main__":
    payload = {
        "type": "push",
        "repo_url": "repo_url",
        "heads": ["head"],
        "commits": ["commit"],
        "time": 0,
        "pushid": 0,
        "user": "user",
        "push_json_url": "push_json_url",
    }
    send_pulse_message(payload)
