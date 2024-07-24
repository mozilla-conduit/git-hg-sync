from kombu.mixins import ConsumerMixin
from mozlog import get_proxy_logger

logger = get_proxy_logger("pluse_consumer")


class Worker(ConsumerMixin):

    def __init__(self, connection, queue, *, repo_synchronyzer):
        self.connection = connection
        self.task_queue = queue
        self.repo_synchronyzer = repo_synchronyzer

    def get_consumers(self, Consumer, channel):
        consumer = Consumer(
            self.task_queue, auto_declare=False, callbacks=[self.on_task]
        )
        return [consumer]

    def on_task(self, body, message):
        logger.info(f"Received message: {body}")
        message.ack()
        raw_entity = body["payload"]
        self.repo_synchronyzer.sync(raw_entity)
