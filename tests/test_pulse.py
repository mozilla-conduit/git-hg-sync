import os

import pytest
from pulse_utils import send_pulse_message

from git_hg_sync import sync

IN_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"


@pytest.fixture
def pulse_config():
    return {
        "userid": "ogiorgis",
        "host": "pulse.mozilla.org",
        "port": 5671,
        "exchange": "exchange/ogiorgis/test",
        "routing_key": "#",
        "queue": "queue/ogiorgis/test",
        "password": os.environ["PULSE_PASSWORD"],
    }


raw_push_entity = {
    "type": "push",
    "repo_url": "repo_url",
    "heads": ["head"],
    "commits": ["commit"],
    "time": 0,
    "pushid": 0,
    "user": "user",
    "push_json_url": "push_json_url",
}

raw_tag_entity = {
    "type": "tag",
    "repo_url": "repo_url",
    "tag": "tag",
    "commit": "commit",
    "time": 0,
    "pushid": 0,
    "user": "user",
    "push_json_url": "push_json_url",
}


@pytest.mark.skipif(IN_GITHUB_ACTIONS, reason="Test doesn't work in Github Actions.")
def test_pulse(pulse_config):
    def mocked_callback(body, message):
        message.ack()
        assert body["payload"] == raw_push_entity

    send_pulse_message(pulse_config, raw_push_entity)
    sync.callback = mocked_callback
    sync.main(pulse_config, True)


def test_callback_with_bad_type():
    with pytest.raises(Exception):
        sync.callback({"payload": {"type": "badType"}}, "message")


def test_parse_entity():
    push_entity = sync.parse_entity(raw_push_entity)
    assert isinstance(push_entity, sync.Push)
    tag_entity = sync.parse_entity(raw_tag_entity)
    assert isinstance(tag_entity, sync.Tag)
