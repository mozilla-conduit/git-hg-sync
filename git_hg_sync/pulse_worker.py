from typing import Any, Protocol

import kombu
from kombu.mixins import ConsumerMixin
from mozlog import get_proxy_logger

from git_hg_sync.events import Push, Tag

logger = get_proxy_logger("pulse_consumer")


class EventHandler(Protocol):
    def __call__(self, event: Push | Tag) -> None:
        pass


class EntityTypeError(Exception):
    pass


class PulseWorker(ConsumerMixin):
    event_handler: EventHandler | None
    """Function that will be called whenever an event is received"""

    def __init__(
        self,
        connection: kombu.Connection,
        queue: kombu.Queue,
        *,
        one_shot: bool = False,
    ) -> None:
        self.connection = connection
        self.task_queue = queue
        self.one_shot = one_shot

    @staticmethod
    def parse_entity(raw_entity: Any) -> Push | Tag:
        logger.debug(f"parse_entity: {raw_entity}")
        message_type = raw_entity.pop("type")
        match message_type:
            case "push":
                return Push(**raw_entity)
            case "tag":
                return Tag(**raw_entity)
            case _:
                raise EntityTypeError(f"unsupported type {message_type}")

    def get_consumers(
        self,
        consumer_class: type[kombu.Consumer],
        _channel: Any,
    ) -> list[kombu.Consumer]:
        consumer = consumer_class(
            self.task_queue, auto_declare=False, callbacks=[self.on_task]
        )
        return [consumer]

    def on_task(self, body: Any, message: kombu.Message) -> None:
        logger.info(f"Received message: {body}")
        raw_entity = body["payload"]
        event = PulseWorker.parse_entity(raw_entity)
        if self.event_handler:
            self.event_handler(event)
        message.ack()
        if self.one_shot:
            self.should_stop = True
