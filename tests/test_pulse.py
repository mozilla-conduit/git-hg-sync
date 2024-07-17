import os

import pytest
from pulse_utils import send_pulse_message

from git_hg_sync import sync


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


payload = {
    "type": "push",
    "repo_url": "repo_url",
    "heads": ["head"],
    "commits": ["commit"],
    "time": 0,
    "pushid": 0,
    "user": "user",
    "push_json_url": "push_json_url",
}


def mocked_callback(body, message):
    message.ack()
    assert body["payload"] == payload


def test_pulse(pulse_config):
    send_pulse_message(pulse_config, payload)
    sync.callback = mocked_callback
    sync.main(pulse_config, True)
