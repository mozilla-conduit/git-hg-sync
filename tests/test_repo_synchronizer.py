from pathlib import Path

import pytest

from git_hg_sync import __main__, repo_synchronizer

HERE = Path(__file__).parent


@pytest.fixture
def pulse_config():
    return {
        "userid": "test_user",
        "host": "pulse.mozilla.org",
        "port": 5671,
        "exchange": "exchange/test_user/test",
        "routing_key": "#",
        "queue": "queue/test_user/test",
        "password": "PULSE_PASSWORD",
    }


@pytest.fixture
def repos_config():
    return {
        "repo_url": {
            "clone": "bad_directory",
            "remote": "remote",
            "target": "target",
        }
    }

def raw_push_entity():
    return {
        "type": "push",
        "repo_url": "repo_url",
        "heads": ["head"],
        "commits": ["commit"],
        "time": 0,
        "pushid": 0,
        "user": "user",
        "push_json_url": "push_json_url",
    }


def raw_tag_entity():
    return {
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
    syncrepos = repo_synchronizer.RepoSynchronyzer(None)
    push_entity = syncrepos.parse_entity(raw_push_entity())
    assert isinstance(push_entity, repo_synchronizer.Push)
    tag_entity = syncrepos.parse_entity(raw_tag_entity())
    assert isinstance(tag_entity, repo_synchronizer.Tag)


def test_sync_process_with_bad_type():
    syncrepos = repo_synchronizer.RepoSynchronyzer(None)
    with pytest.raises(repo_synchronizer.EntityTypeError):
        syncrepos.sync({"type": "badType"})


def test_sync_process_with_bad_repo(repos_config):
    syncrepos = repo_synchronizer.RepoSynchronyzer(repos_config=repos_config)
    with pytest.raises(AssertionError) as e:
        syncrepos.sync(raw_push_entity())
    assert str(e.value) == f"clone {repos_config['repo_url']['clone']} doesn't exists"


def test_get_connection_and_queue(pulse_config):
    connection = __main__.get_connection(pulse_config)
    queue = __main__.get_queue(pulse_config)
    assert connection.userid == pulse_config["userid"]
    assert connection.host == f"{pulse_config['host']}:{pulse_config['port']}"
    assert queue.name == pulse_config["queue"]
