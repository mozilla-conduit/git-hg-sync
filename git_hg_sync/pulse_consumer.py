from kombu.mixins import ConsumerMixin
from mozlog import get_proxy_logger

from git_hg_sync import sync_repos

logger = get_proxy_logger("pluse_consumer")


class Worker(ConsumerMixin):

    def __init__(self, connection, queue):
        self.connection = connection
        self.task_queue = queue

    def get_consumers(self, Consumer, channel):
        consumer = Consumer(
            self.task_queue, auto_declare=False, callbacks=[self.on_task]
        )
        return [consumer]

    def on_task(self, body, message):
        logger.info(f"Received message: {body}")
        message.ack()
        raw_entity = body["payload"]
        sync_repos.process(raw_entity)
