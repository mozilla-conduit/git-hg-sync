import logging
from datetime import datetime

import kombu

from git_hg_sync import config

logger = logging.getLogger()


def send_pulse_message(pulse_config, payload, queue=None):
    """Send a pulse message
    The routing key will be constructed from the repository URL.
    The Pulse message will be constructed from the specified payload
    and sent to the requested exchange.
    if queue is not None, create queue
    """
    userid = pulse_config["userid"]
    password = pulse_config["password"]
    routing_key = pulse_config["routing_key"]
    host = pulse_config["host"]
    port = pulse_config["port"]
    exchange = pulse_config["exchange"]
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
        "repo_url": "git_repo",
        "heads": ["head"],
        "commits": ["commit_sha_1", "commit_sha_2"],
        "time": 0,
        "pushid": 0,
        "user": "user",
        "push_json_url": "push_json_url",
    }
    pulse_conf = config.get_config()["pulse"]
    send_pulse_message(pulse_conf, payload)
