import logging
import os
from datetime import datetime

import kombu

logger = logging.getLogger()


def send_pulse_message(userid, password, exchange, host, payload, queue=None):
    """Send a pulse message
    The routing key will be constructed from the repository URL.
    The Pulse message will be constructed from the specified payload
    and sent to the requested exchange.
    if queue is not None, create queue
    """

    routing_key = "test"
    port = 5671

    logger.info(f"connecting to pulse at {host}:{port} as {userid}")

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
    userid = "ogiorgis"
    exchange = "exchange/ogiorgis/test"
    host = "pulse.mozilla.org"
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
    password = os.environ["PULSE_PASSWORD"]
    send_pulse_message(userid, password, exchange, host, payload)
