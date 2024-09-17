import subprocess
from pathlib import Path

import pytest
from git import Repo
from utils import hg_cat

from git_hg_sync.__main__ import get_connection, get_queue
from git_hg_sync.config import TrackedRepository, PulseConfig
from git_hg_sync.repo_synchronizer import RepoSynchronizer
from git_hg_sync.mapping import SyncBranchOperation, SyncTagOperation


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
    # Create a remote mercurial repository
    hg_remote_repo_path = tmp_path / "hg-remotes" / "myrepo"
    hg_remote_repo_path.mkdir(parents=True)
    subprocess.run(["hg", "init"], cwd=hg_remote_repo_path, check=True)

    # Create a remote git repository
    git_remote_repo_path = tmp_path / "git-remotes" / "myrepo"
    # Create an initial commit on git
    repo = Repo.init(git_remote_repo_path)
    foo_path = git_remote_repo_path / "foo.txt"
    foo_path.write_text("FOO CONTENT")
    repo.index.add([foo_path])
    repo.index.commit("add foo.txt").hexsha

    # Push to mercurial repository
    subprocess.run(
        [
            "git",
            "push",
            "hg::" + str(hg_remote_repo_path),
            "master:refs/heads/branches/bar/tip",
        ],
        cwd=git_remote_repo_path,
        check=True,
    )

    # Create a branch in mercurial repository for tags to live in
    subprocess.run(["hg", "branch", "tags"], cwd=hg_remote_repo_path, check=True)
    tags_branch_test_file = hg_remote_repo_path / "README.md"
    tags_branch_test_file.write_text("This branch contains tags.")
    subprocess.run(
        ["hg", "add", str(tags_branch_test_file)], cwd=hg_remote_repo_path, check=True
    )
    subprocess.run(
        ["hg", "commit", "-m", "create tag branch"], cwd=hg_remote_repo_path, check=True
    )

    # Create a new commit on git repo
    bar_path = git_remote_repo_path / "bar.txt"
    bar_path.write_text("BAR CONTENT")
    repo.index.add([bar_path])
    git_commit_sha = repo.index.commit("add bar.txt").hexsha

    # Sync new commit with mercurial repository
    git_local_repo_path = tmp_path / "clones" / "myrepo"
    syncrepos = RepoSynchronizer(git_local_repo_path, str(git_remote_repo_path))
    operations: list[SyncBranchOperation | SyncTagOperation] = [
        SyncBranchOperation(source_commit=git_commit_sha, destination_branch="bar"),
        SyncTagOperation(
            source_commit=git_commit_sha, tag="mytag", tags_destination_branch="tags"
        ),
    ]

    syncrepos.sync(str(hg_remote_repo_path), operations)

    # test
    assert "BAR CONTENT" in hg_cat(hg_remote_repo_path, "bar.txt", "bar")

    assert "BAR CONTENT" in hg_cat(hg_remote_repo_path, "bar.txt", "mytag")


def test_get_connection_and_queue(pulse_config: PulseConfig) -> None:
    connection = get_connection(pulse_config)
    queue = get_queue(pulse_config)
    assert connection.userid == pulse_config.userid
    assert connection.host == f"{pulse_config.host}:{pulse_config.port}"
    assert queue.name == pulse_config.queue
