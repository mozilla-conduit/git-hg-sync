import os

import pulse_utils
import pytest

from git_hg_sync.config import PulseConfig

NO_RABBITMQ = not (os.getenv("RABBITMQ") == "true")


@pytest.fixture
def pulse_config():
    return PulseConfig(
        **{
            "userid": "guest",
            "host": "pulse",
            "port": 5672,
            "exchange": "exchange/guest/test",
            "routing_key": "#",
            "queue": "queue/guest/test",
            "password": "guest",
        }
    )


@pytest.mark.skipif(NO_RABBITMQ, reason="Test doesn't work without rabbitMq")
def test_send(pulse_config):
    payload = {
        "type": "tag",
        "repo_url": "repo.git",
        "tag": "Tag",
        "commit": "sha",
        "time": 0,
        "pushid": 0,
        "user": "user",
        "push_json_url": "push_json_url",
    }
    pulse_utils.send_pulse_message(pulse_config, payload, ssl=False)
