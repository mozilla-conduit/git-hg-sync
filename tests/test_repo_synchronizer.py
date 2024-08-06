from pathlib import Path

import pytest

from git_hg_sync.__main__ import get_connection, get_queue
from git_hg_sync.config import (
    Mapping,
    MappingSource,
    MappingDestination,
    PulseConfig,
    TrackedRepository,
)
from git_hg_sync.repo_synchronizer import RepoSynchronizer
from git_hg_sync.events import Push


@pytest.fixture
def pulse_config():
    return PulseConfig(
        **{
            "userid": "test_user",
            "host": "pulse.mozilla.org",
            "port": 5671,
            "exchange": "exchange/test_user/test",
            "routing_key": "#",
            "queue": "queue/test_user/test",
            "password": "PULSE_PASSWORD",
        }
    )


@pytest.fixture
def tracked_repositories() -> list[TrackedRepository]:
    return [
        TrackedRepository(
            name="myrepo",
            url="https://gitforge.example/myrepo",
        )
    ]


@pytest.fixture
def mappings() -> list[Mapping]:
    return [
        Mapping(
            source=MappingSource(
                url="https://gitforge.example/myrepo",
                branch_pattern="branch1",
            ),
            destination=MappingDestination(
                branch="branch",
                url="https://hgforge/myrepo",
            ),
        )
    ]


def test_sync_process_with_bad_repo(
    tmp_path: Path,
    tracked_repositories: list[TrackedRepository],
    mappings: list[Mapping],
) -> None:
    syncrepos = RepoSynchronizer(tmp_path / "clones", tracked_repositories, mappings)
    syncrepos.sync(
        Push(
            repo_url="repo_url",
            branches={"branch1": "anothercommitsha"},
            time=0,
            pushid=0,
            user="user",
            push_json_url="push_json_url",
        )
    )
    # TODO finish that test (check that warning was triggered)


def test_get_connection_and_queue(pulse_config):
    connection = get_connection(pulse_config)
    queue = get_queue(pulse_config)
    assert connection.userid == pulse_config.userid
    assert connection.host == f"{pulse_config.host}:{pulse_config.port}"
    assert queue.name == pulse_config.queue
