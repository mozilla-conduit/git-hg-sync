import logging
from dataclasses import dataclass

from git_hg_sync import config
from git_hg_sync.git_cinnabar import git_cinnabar_process
from git_hg_sync.pulse_consumer import get_connection, get_consumer

PULSE_TIMEOUT = 6
logger = logging.getLogger()


@dataclass
class Push:
    type: str
    repo_url: str
    heads: list[str]
    commits: list[str]
    time: int
    pushid: int
    user: str
    push_json_url: str


@dataclass
class Tag:
    type: str
    repo_url: str
    tag: str
    commit: str
    time: int
    pushid: int
    user: str
    push_json_url: str


def parse_entity(raw_entity):
    if raw_entity["type"] == "push":
        entity = Push(**raw_entity)
    elif raw_entity["type"] == "tag":
        entity = Tag(**raw_entity)
    else:
        raise Exception(f"unsupported type message {raw_entity['type']}")
    return entity


def callback(body, message):
    logger.debug(f"Received message: {body}")
    raw_entity = body["payload"]
    entity = parse_entity(raw_entity)
    message.ack()
    git_cinnabar_process(entity)


def main(pulse_conf, one_time=False):
    logging.basicConfig(level=logging.INFO)
    with get_connection(pulse_conf) as connection:
        with get_consumer(pulse_conf, connection, [callback]):
            while True:
                try:
                    connection.drain_events(timeout=PULSE_TIMEOUT)
                except TimeoutError:
                    if one_time:
                        break
                    logger.info("waiting for messages")


if __name__ == "__main__":
    pulse_conf = config.get_config()["pulse"]
    main(pulse_conf)
