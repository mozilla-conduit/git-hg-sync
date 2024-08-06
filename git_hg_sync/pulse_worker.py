from kombu.mixins import ConsumerMixin
from mozlog import get_proxy_logger

from git_hg_sync.events import Push, Tag

logger = get_proxy_logger("pluse_consumer")


class EntityTypeError(Exception):
    pass


class PulseWorker(ConsumerMixin):

    def __init__(self, connection, queue, *, repo_synchronyzer):
        self.connection = connection
        self.task_queue = queue
        self.repo_synchronyzer = repo_synchronyzer

    @staticmethod
    def parse_entity(raw_entity):
        logger.debug(f"parse_entity: {raw_entity}")
        message_type = raw_entity.pop("type")
        match message_type:
            case "push":
                return Push(**raw_entity)
            case "tag":
                return Tag(**raw_entity)
            case _:
                raise EntityTypeError(f"unsupported type {message_type}")

    def get_consumers(self, Consumer, channel):
        consumer = Consumer(
            self.task_queue, auto_declare=False, callbacks=[self.on_task]
        )
        return [consumer]

    def on_task(self, body, message):
        logger.info(f"Received message: {body}")
        message.ack()
        raw_entity = body["payload"]
        parsed_message = PulseWorker.parse_entity(raw_entity)
        self.repo_synchronyzer.sync(parsed_message)
