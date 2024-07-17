from dataclasses import dataclass

from git_hg_sync import config
from git_hg_sync.git_cinnabar import git_cinnabar_process
from git_hg_sync.pulse_consumer import get_connection, get_consumer

PULSE_TIMEOUT = 6


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
    commits: str
    time: int
    pushid: int
    user: str
    push_json_url: str


def callback(body, message):
    print("Received message: %s" % body)
    payload = body["payload"]
    if payload["type"] == "push":
        entity = Push(**payload)
    elif payload["type"] == "tag":
        entity = Tag(**payload)
    else:
        raise Exception(f"unsupported type message {payload['type']}")
    message.ack()
    git_cinnabar_process(entity)


def main(pulse_conf, one_time=False):
    with get_connection(pulse_conf) as connection:
        with get_consumer(pulse_conf, connection, [callback]):
            while True:
                try:
                    connection.drain_events(timeout=PULSE_TIMEOUT)
                except TimeoutError:
                    if one_time:
                        break
                    print("waiting for messages")


if __name__ == "__main__":
    pulse_conf = config.get_config()["pulse"]
    main(pulse_conf)
