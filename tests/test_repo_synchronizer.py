import subprocess
from collections.abc import Callable
from pathlib import Path
from unittest import mock

import pytest
from git import Repo
from git.exc import GitCommandError
from utils import hg_cat, hg_log, hg_rev

from git_hg_sync import repo_synchronizer
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
def make_hg_repo() -> Callable:
    def _make_hg_repo(path: Path, repo_name: str) -> Path:
        hg_remote_repo_path = path / "hg-remotes" / repo_name
        hg_remote_repo_path.mkdir(parents=True)
        subprocess.run(["hg", "init"], cwd=hg_remote_repo_path, check=True)

        return hg_remote_repo_path

    return _make_hg_repo


@pytest.fixture
def hg_destination(make_hg_repo: Callable, tmp_path: Path) -> Path:
    return make_hg_repo(tmp_path, "myrepo")


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


@pytest.mark.parametrize("existing_tags_branch", [False, True])
def test_sync_process(
    git_source: Repo,
    hg_destination: Path,
    tmp_path: Path,
    existing_tags_branch: bool,
) -> None:
    branch = "bar"
    tag_branch = "tags"
    tag = "mytag"
    tag_suffix = "some suffix"

    repo = Repo(git_source)

    if existing_tags_branch:
        # Create a branch in mercurial repository for tags to live in
        subprocess.run(["hg", "branch", tag_branch], cwd=hg_destination, check=True)
        tags_branch_test_file = hg_destination / "README.md"
        tags_branch_test_file.write_text("This branch contains tags.")
        subprocess.run(
            ["hg", "add", str(tags_branch_test_file)],
            cwd=hg_destination,
            check=True,
        )
        subprocess.run(
            ["hg", "commit", "-m", f"create {tag_branch}"],
            cwd=hg_destination,
            check=True,
        )

    # Create a new commit on git repo
    bar_path = git_source / "bar.txt"
    bar_path.write_text("BAR CONTENT")
    repo.index.add([bar_path])
    git_commit_sha = repo.index.commit("add bar.txt").hexsha

    # Sync new commit with mercurial repository.
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
    user_info = "request_user"  # The part before the @ in request_user.
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

    tag_author = hg_log(hg_destination, tag_branch, ["-T", "{author}"])
    assert f"{user_info} <{request_user}>" in tag_author

    # We want to make sure we have pushed in multiple steps. Unfortunately, we cannot do
    # it with a MagicMock on Git.push, as GitPython does Python magic to redirect
    # commands to `git` without defining them as methods on the class.
    #
    # We expect to have pushed tags last, so only one file, .hgtags, should have been
    # changed.
    #
    # So here's a very dodgy way of testing how many files the last push has touched.
    # We check .hg/store/undo, and it should only list files impacted by the last push,
    # as well as two metadata files.
    with (hg_destination / ".hg" / "store" / "undo").open() as undo:
        undo_log = undo.read()
        assert ".hgtags" in undo_log
        assert "bar.txt" not in undo_log
        assert len(undo_log.strip().split("\n")) == 3, (
            "An unexpected number of files was changed in the last push"
        )


def test_sync_process_duplicate_tags(
    git_source: Repo,
    hg_destination: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Processing duplicate tags should be a successful noop."""

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

    logger_mock = mock.MagicMock()
    monkeypatch.setattr(repo_synchronizer, "logger", logger_mock)
    syncrepos.sync(str(hg_destination), operations, request_user)

    # As we can't mock the GitPython logic, we inspect our debug logs instead.
    assert any(
        f"Push arguments: ['-f', 'hg::{hg_destination}', " in warning.args[0]
        for warning in logger_mock.debug.call_args_list
    ), "Expected a force-push of the non-existent tag branch on first run."

    # Re-run the operation
    second_logger_mock = mock.MagicMock()
    monkeypatch.setattr(repo_synchronizer, "logger", second_logger_mock)
    syncrepos.sync(str(hg_destination), operations, request_user)

    # The last warning should tell us about the duplicate tags.
    assert (
        f"Tag {tag} already exists"
        in second_logger_mock.warning.call_args_list[-1].args[0]
    ), "Expected a warning about tag duplication."
    assert any(
        f"Push arguments: ['hg::{hg_destination}', " in warning.args[0]
        for warning in second_logger_mock.debug.call_args_list
    ), "Expected a non force-push of the now-existent tag branch on second run."

    # Test the tag commit message.
    tag_log = hg_log(hg_destination, tag_branch, ["-T", "{desc}"])
    assert tag in tag_log


def test_sync_process_no_duplicate_tags_on_error(
    git_source: Repo,
    hg_destination: Path,
    tmp_path: Path,
) -> None:
    """Reprocessing a tag message after a failure should not lead to duplicate tags."""

    tag_branch = "tags"
    tag = "mytag"
    tag_suffix = "some suffix"

    repo = Repo(git_source)

    git_commit_sha = repo.rev_parse("HEAD")

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

    # Make the target repo unwriteable,, so the next syncs fail.
    failhook = """
[hooks]
pretxnchangegroup.reject = /bin/false
    """
    hgrc = hg_destination / ".hg" / "hgrc"
    with Path.open(hgrc, "w") as f:
        f.write(failhook)

    with pytest.raises(GitCommandError):
        syncrepos.sync(str(hg_destination), operations, request_user)

    # Re-run the operation without the blocking hook.
    hgrc.unlink()
    syncrepos.sync(str(hg_destination), operations, request_user)

    # Test the tag commit message.
    git_tag_log = Repo(str(git_local_repo_path)).git.execute(
        ["git", "log", "--oneline", tag_branch]
    )
    assert len(git_tag_log.strip().split("\n")) == 1, (
        "Found more than one commit on the tags branch in the Git workdir"
    )

    # Test the tag commit message.
    hg_tag_log = hg_log(hg_destination, f"..{tag_branch}", ["-T", "{desc}\n"])
    assert len(hg_tag_log.strip().split("\n")) == 1, (
        "Found more than one commit on the tags branch in Mercurial"
    )


def test_sync_process_multiple_destinations(
    make_hg_repo: Callable,
    git_source: Repo,
    hg_destination: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Processing the same tag to multiple destinations should update all repos."""
    tag_branch = "tags"
    tag = "mytag"
    tag_suffix = "some suffix"

    hg_destination2 = make_hg_repo(tmp_path, "second_repo")

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

    # Sync the tags to the second repo.
    logger_mock = mock.MagicMock()
    monkeypatch.setattr(repo_synchronizer, "logger", logger_mock)
    syncrepos.sync(str(hg_destination2), operations, request_user)

    # Test the tag commit message.
    tag_log = hg_log(hg_destination2, tag_branch, ["-T", "{desc}"])
    assert tag in tag_log


def test_get_connection_and_queue(pulse_config: PulseConfig) -> None:
    connection = get_connection(pulse_config)
    queue = get_queue(pulse_config)
    assert connection.userid == pulse_config.userid
    assert connection.host == f"{pulse_config.host}:{pulse_config.port}"
    assert queue.name == pulse_config.queue
