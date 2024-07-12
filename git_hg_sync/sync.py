from dataclasses import dataclass

from git_hg_sync.pulse_consumer import get_connection, get_consumer

DELAY = 6


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
        push = Push(**payload)
        print(push)
    elif payload["type"] == "tag":
        tag = Tag(**payload)
        print(tag)
    else:
        raise Exception(f"unsupported type message {payload['type']}")
    message.ack()


def main(one_time=False):
    with get_connection() as connection:
        with get_consumer(connection, [callback]):
            while True:
                try:
                    connection.drain_events(timeout=DELAY)
                except TimeoutError:
                    if one_time:
                        break
                    print("waiting for messages")


if __name__ == "__main__":
    main()
