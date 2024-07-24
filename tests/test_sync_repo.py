from pathlib import Path

import mozlog
import pytest

from git_hg_sync import __main__, sync_repos

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


def setup_module():
    logger = mozlog.structuredlog.StructuredLogger("tests")
    mozlog.structuredlog.set_default_logger(logger)


def test_parse_entity():
    syncrepos = sync_repos.RepoSynchronyzer(None)
    push_entity = syncrepos.parse_entity(raw_push_entity)
    assert isinstance(push_entity, sync_repos.Push)
    tag_entity = syncrepos.parse_entity(raw_tag_entity)
    assert isinstance(tag_entity, sync_repos.Tag)


def test_sync_process_with_bad_type():
    syncrepos = sync_repos.RepoSynchronyzer(None)
    with pytest.raises(sync_repos.EntityTypeError):
        syncrepos.sync({"type": "badType"})


def test_sync_process_with_bad_repo(repos_config):
    syncrepos = sync_repos.RepoSynchronyzer(repos_config=repos_config)
    with pytest.raises(AssertionError) as e:
        syncrepos.sync(raw_push_entity)
    assert str(e.value) == f"clone {repos_config['repo_url']['clone']} doesn't exists"


def test_get_connection_and_queue(pulse_config):
    connection = __main__.get_connection(pulse_config)
    queue = __main__.get_queue(pulse_config)
    assert connection.userid == pulse_config["userid"]
    assert connection.host == f"{pulse_config['host']}:{pulse_config['port']}"
    assert queue.name == pulse_config["queue"]
