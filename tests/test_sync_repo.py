import os
from pathlib import Path

import pytest

from git_hg_sync import config, service, sync_repos

HERE = Path(__file__).parent


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


def test_parse_entity():
    push_entity = sync_repos.parse_entity(raw_push_entity)
    assert isinstance(push_entity, sync_repos.Push)
    tag_entity = sync_repos.parse_entity(raw_tag_entity)
    assert isinstance(tag_entity, sync_repos.Tag)


def test_sync_process_with_bad_type():
    with pytest.raises(AttributeError):
        sync_repos.process({"type": "badType"})


def test_get_connection_and_queue():
    pulse_conf = config.get_pulse_config(HERE / "config_test.ini")["pulse"]
    connection = service.get_connection(pulse_conf)
    queue = service.get_queue(pulse_conf)
    assert connection.userid == pulse_conf["userid"]
    assert connection.host == f"{pulse_conf['host']}:{pulse_conf['port']}"
    assert queue.name == pulse_conf["queue"]