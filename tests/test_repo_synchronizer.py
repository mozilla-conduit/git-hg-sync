from pathlib import Path

import pytest

from git_hg_sync.__main__ import get_connection, get_queue
from git_hg_sync.repo_synchronizer import RepoSynchronyzer, Push

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


def test_sync_process_with_bad_repo(repos_config):
    syncrepos = RepoSynchronyzer(repos_config=repos_config)
    with pytest.raises(AssertionError) as e:
        syncrepos.sync(Push(repo_url="repo_url", heads=["head"], commits=["commits"], time=0, pushid=0, user="user", push_json_url="push_json_url"))
    assert str(e.value) == f"clone {repos_config['repo_url']['clone']} doesn't exists"


def test_get_connection_and_queue(pulse_config):
    connection = get_connection(pulse_config)
    queue = get_queue(pulse_config)
    assert connection.userid == pulse_config["userid"]
    assert connection.host == f"{pulse_config['host']}:{pulse_config['port']}"
    assert queue.name == pulse_config["queue"]
