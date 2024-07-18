from kombu import Connection, Exchange, Queue


def get_connection(pulse_conf):
    return Connection(
        hostname=pulse_conf["host"],
        port=pulse_conf["port"],
        userid=pulse_conf["userid"],
        password=pulse_conf["password"],
        ssl=True,
    )


def get_consumer(pulse_conf, connection, callbacks):
    exchange = pulse_conf["exchange"]
    exchange = Exchange(exchange, type="topic")
    exchange(connection).declare(
        passive=True
    )  # raise an error if exchange doesn't exist

    queue = Queue(
        name=pulse_conf["queue"],
        exchange=exchange,
        routing_key=pulse_conf["routing_key"],
        durable=True,
        exclusive=False,
        auto_delete=False,
    )

    consumer = connection.Consumer(queue, auto_declare=False, callbacks=callbacks)
    consumer.queues[0].queue_declare()
    consumer.queues[0].queue_bind()
    return consumer
