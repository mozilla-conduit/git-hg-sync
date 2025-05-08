import subprocess
from pathlib import Path

import pytest
from git import Repo
from utils import hg_cat, hg_log, hg_rev

from git_hg_sync.__main__ import get_connection, get_queue
from git_hg_sync.config import PulseConfig, TrackedRepository
from git_hg_sync.mapping import SyncBranchOperation, SyncTagOperation
from git_hg_sync.repo_synchronizer import RepoSynchronizer


@pytest.fixture
def tracked_repositories() -> list[TrackedRepository]:
    return [
        TrackedRepository(
            name="myrepo",
            url="https://gitforge.example/myrepo",
        )
    ]


@pytest.fixture
def hg_destination(tmp_path: Path) -> Path:
    hg_remote_repo_path = tmp_path / "hg-remotes" / "myrepo"
    hg_remote_repo_path.mkdir(parents=True)
    subprocess.run(["hg", "init"], cwd=hg_remote_repo_path, check=True)

    return hg_remote_repo_path


@pytest.fixture
def git_source(hg_destination: Path, tmp_path: Path) -> Path:
    # Create a remote mercurial repository

    # Create a remote git repository
    git_remote_repo_path = tmp_path / "git-remotes" / "myrepo"
    # Create an initial commit on git
    repo = Repo.init(git_remote_repo_path)
    foo_path = git_remote_repo_path / "foo.txt"
    foo_path.write_text("FOO CONTENT")
    repo.index.add([foo_path])
    repo.index.commit("add foo.txt")

    # Push to mercurial repository
    subprocess.run(
        [
            "git",
            "push",
            "hg::" + str(hg_destination),
            "master:refs/heads/branches/bar/tip",
        ],
        cwd=git_remote_repo_path,
        check=True,
    )

    return git_remote_repo_path


def test_sync_process_(
    git_source: Repo,
    hg_destination: Path,
    tmp_path: Path,
) -> None:
    branch = "bar"
    tag_branch = "tags"
    tag = "mytag"
    tag_suffix = "some suffix"

    repo = Repo(git_source)

    # Create a new commit on git repo
    bar_path = git_source / "bar.txt"
    bar_path.write_text("BAR CONTENT")
    repo.index.add([bar_path])
    git_commit_sha = repo.index.commit("add bar.txt").hexsha

    # Sync new commit with mercurial repository
    git_local_repo_path = tmp_path / "clones" / "myrepo"
    syncrepos = RepoSynchronizer(git_local_repo_path, str(git_source))
    operations: list[SyncBranchOperation | SyncTagOperation] = [
        SyncBranchOperation(source_commit=git_commit_sha, destination_branch=branch),
        SyncTagOperation(
            source_commit=git_commit_sha,
            tag=tag,
            tags_destination_branch=tag_branch,
            tag_message_suffix=tag_suffix,
        ),
    ]

    request_user = "request_user@example.com"
    syncrepos.sync(str(hg_destination), operations, request_user)

    # test
    assert "BAR CONTENT" in hg_cat(hg_destination, "bar.txt", branch)
    assert "BAR CONTENT" in hg_cat(hg_destination, "bar.txt", tag)

    # test tag commit message
    tag_log = hg_log(hg_destination, tag_branch, ["-T", "{desc}"])
    assert "No bug - Tagging" in tag_log
    assert tag_suffix in tag_log
    assert tag in tag_log
    assert hg_rev(hg_destination, branch) in tag_log


def test_sync_process_duplicate_tags(
    git_source: Repo,
    hg_destination: Path,
    tmp_path: Path,
) -> None:
    tag_branch = "tags"
    tag = "mytag"
    tag_suffix = "some suffix"

    repo = Repo(git_source)

    git_commit_sha = repo.rev_parse("HEAD")

    # Sync new commit with mercurial repository
    git_local_repo_path = tmp_path / "clones" / "myrepo"
    syncrepos = RepoSynchronizer(git_local_repo_path, str(git_source))
    operations: list[SyncBranchOperation | SyncTagOperation] = [
        SyncTagOperation(
            source_commit=git_commit_sha,
            tag=tag,
            tags_destination_branch=tag_branch,
            tag_message_suffix=tag_suffix,
        ),
    ]

    request_user = "request_user@example.com"
    syncrepos.sync(str(hg_destination), operations, request_user)
    # Re-run the operation
    syncrepos.sync(str(hg_destination), operations, request_user)

    # test tag commit message
    tag_log = hg_log(hg_destination, tag_branch, ["-T", "{desc}"])
    assert tag in tag_log


def test_get_connection_and_queue(pulse_config: PulseConfig) -> None:
    connection = get_connection(pulse_config)
    queue = get_queue(pulse_config)
    assert connection.userid == pulse_config.userid
    assert connection.host == f"{pulse_config.host}:{pulse_config.port}"
    assert queue.name == pulse_config.queue
