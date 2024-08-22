import subprocess
from pathlib import Path

import pytest
from git import Repo

from git_hg_sync.__main__ import get_connection, get_queue
from git_hg_sync.config import PulseConfig, TrackedRepository
from git_hg_sync.repo_synchronizer import RepoSynchronizer


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
            "ssl": True,
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


def test_sync_process_(
    tmp_path: Path,
) -> None:

    # Create a remote git repository
    git_remote_repo_path = tmp_path / "git-remotes" / "myrepo"
    repo = Repo.init(git_remote_repo_path)
    foo_path = git_remote_repo_path / "foo.txt"
    foo_path.write_text("FOO CONTENT")
    repo.index.add([foo_path])
    git_commit_sha = repo.index.commit("add foo.txt").hexsha

    # Create a remote mercurial repository
    hg_remote_repo_path = tmp_path / "hg-remotes" / "myrepo"
    hg_remote_repo_path.mkdir(parents=True)
    subprocess.run(["hg", "init"], cwd=hg_remote_repo_path, check=True)

    git_local_repo_path = tmp_path / "clones" / "myrepo"

    syncrepos = RepoSynchronizer(git_local_repo_path, str(git_remote_repo_path))
    syncrepos.sync_branches(str(hg_remote_repo_path), [(git_commit_sha, "foo")])

    process = subprocess.run(
        ["hg", "export", "tip"],
        cwd=hg_remote_repo_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "FOO CONTENT" in process.stdout


def test_get_connection_and_queue(pulse_config):
    connection = get_connection(pulse_config)
    queue = get_queue(pulse_config)
    assert connection.userid == pulse_config.userid
    assert connection.host == f"{pulse_config.host}:{pulse_config.port}"
    assert queue.name == pulse_config.queue
