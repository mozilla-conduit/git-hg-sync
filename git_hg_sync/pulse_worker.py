import json
from typing import Any, Protocol

import kombu
from kombu.mixins import ConsumerMixin
from mozlog import get_proxy_logger
from pydantic import ValidationError

from git_hg_sync.events import Event, Push

logger = get_proxy_logger("pulse_consumer")


class EventHandler(Protocol):
    def __call__(self, event: Event) -> None:
        pass


class EntityTypeError(Exception):
    pass


class PulseWorker(ConsumerMixin):
    event_handler: EventHandler | None
    """Function that will be called whenever an event is received"""

    consumer: kombu.Consumer | None = None

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
    def parse_entity(raw_entity: dict) -> Event:
        logger.debug(f"parse_entity: {raw_entity}")
        message_type = raw_entity.pop("type")
        match message_type:
            case "push":
                return Push(**raw_entity)
            case _:
                raise EntityTypeError(f"unsupported type {message_type}")

    def get_consumers(
        self,
        consumer_class: type[kombu.Consumer],
        _channel: Any,
    ) -> list[kombu.Consumer]:
        if not self.consumer:
            self.consumer = consumer_class(
                self.task_queue, auto_declare=False, callbacks=[self.on_task]
            )
            logger.debug(f"Created consumer {self.consumer=}")
        return [self.consumer]

    def on_connection_error(self, exc: Exception, interval: int) -> None:
        logger.error(f"Connection error: {exc=}, retrying in {interval}s ...")

    def on_task(self, body: Any, message: kombu.Message) -> None:
        logger.info(f"Received message: {body}")

        if isinstance(body, str):
            logger.debug("Message is a string. Trying to parse as JSON ...")
            try:
                body = json.loads(body)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON message, rejecting ... `{e}`")
                message.reject()
                return

        if not isinstance(body, dict):
            logger.warning(f"Invalid message data, rejecting ... `{body}`")
            message.reject()
            return

        if not (raw_entity := body.get("payload")):
            logger.warning(f"Missing or empty payload, rejecting ... `{body}`")
            message.reject()
            return

        if not isinstance(raw_entity, dict):
            logger.warning(f"Invalid payload, rejecting ... `{raw_entity}`")
            message.reject()
            return

        try:
            event = PulseWorker.parse_entity(raw_entity)
        except KeyError as e:
            logger.warning(
                f"Invalid payload: missing {e}, rejecting ... `{raw_entity}`"
            )
            message.reject()
            return
        except (EntityTypeError, TypeError, ValidationError) as e:
            logger.warning(f"Invalid payload: {e}, rejecting ... `{raw_entity}`")
            message.reject()
            return

        try:
            if self.event_handler:
                self.event_handler(event)
        except:  # noqa: E722
            message.requeue()
        else:
            message.ack()

        if self.one_shot:
            self.should_stop = True
