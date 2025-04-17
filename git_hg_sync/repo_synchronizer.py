import os
from functools import partial
from pathlib import Path

from git import Repo, exc
from mozlog import get_proxy_logger

from git_hg_sync.mapping import SyncBranchOperation, SyncOperation, SyncTagOperation
from git_hg_sync.retry import retry

logger = get_proxy_logger("sync_repo")

GIT_SSH_COMMAND_ENV_VAR = "GIT_SSH_COMMAND"
REQUEST_USER_ENV_VAR = "AUTOLAND_REQUEST_USER"


class RepoSyncError(Exception):
    """Base exception class for git to mercurial synchronization errors"""


class MercurialMetadataNotFoundError(RepoSyncError):
    """Raised when a commit is not found"""


class RepoSynchronizer:
    def __init__(
        self,
        clone_directory: Path,
        url: str,
    ) -> None:
        self._clone_directory = clone_directory
        self._src_remote = url

    def _get_clone_repo(self) -> Repo:
        """Get a GitPython Repo object pointing to a git clone of the source
        remote."""
        if self._clone_directory.exists():
            repo = Repo(self._clone_directory)
        else:
            repo = Repo.init(self._clone_directory)

        # Ensure that the clone repository is well configured
        with repo.config_writer() as config:
            config.add_section("cinnabar")
            config.set("cinnabar", "experiments", "branch,tag,git_commit,merge")
        return repo

    def _commit_has_mercurial_metadata(self, repo: Repo, git_commit: str) -> bool:
        stdout = repo.git.cinnabar(["git2hg", git_commit])
        return not all(char == "0" for char in stdout.strip())

    def _fetch_all_from_remote(self, repo: Repo, remote: str) -> None:
        try:
            repo.git.fetch([remote])
        except exc.GitCommandError as e:
            # can't fetch if repo is empty
            if "fatal: couldn't find remote ref HEAD" in e.stderr:
                raise e

    def sync(
        self, destination_url: str, operations: list[SyncOperation], request_user: str
    ) -> None:
        logger.info(f"Syncing {operations} to {destination_url} ...")
        try:
            repo = self._get_clone_repo()
        except PermissionError as exc:
            raise PermissionError(
                f"Failed to create local clone from {destination_url}"
            ) from exc

        destination_remote = f"hg::{destination_url}"

        # Ensure we have all commits from destination repository
        retry(
            "fetching commits from destination",
            lambda: self._fetch_all_from_remote(repo, destination_remote),
        )

        # Get commits we want to send to destination repository
        commits_to_fetch = [operation.source_commit for operation in operations]
        retry(
            "fetching source commits",
            lambda: repo.git.fetch([self._src_remote, *commits_to_fetch]),
        )
        push_args = [destination_remote]

        # Handle branch operations
        branch_ops: list[SyncBranchOperation] = [
            op for op in operations if isinstance(op, SyncBranchOperation)
        ]
        for branch_operation in branch_ops:
            try:
                push_args.append(
                    f"{branch_operation.source_commit}:refs/heads/branches/{branch_operation.destination_branch}/tip"
                )
            except Exception as e:
                raise RepoSyncError(branch_operation, e) from e

        os.environ[REQUEST_USER_ENV_VAR] = request_user
        logger.debug(f"{REQUEST_USER_ENV_VAR} set to {request_user}")

        # Add mercurial metadata to new commits from synced branches
        # Some of these commits could be tagged in the same synchronization and
        # tagging can only be done on a commit that already have mercurial
        # metadata
        if branch_ops:
            retry(
                "adding mercurial metadata to git commits",
                lambda: repo.git.execute(
                    ["git"]
                    + ["-c", "cinnabar.data=force"]
                    + ["push"]
                    + ["--dry-run"]
                    + push_args,
                ),
            )
        # Handle tag operations
        tag_ops: list[SyncTagOperation] = [
            op for op in operations if isinstance(op, SyncTagOperation)
        ]

        # Create tag branches locally
        tag_branches = {op.tags_destination_branch for op in tag_ops}
        for tag_branch in tag_branches:
            retry(
                "getting tag branch from destination",
                # https://docs.python-guide.org/writing/gotchas/#late-binding-closures
                partial(
                    repo.git.fetch,
                    [
                        "-f",
                        destination_remote,
                        f"refs/heads/branches/{tag_branch}/tip:{tag_branch}",
                    ],
                ),
            )
            push_args.append(f"{tag_branch}:refs/heads/branches/{tag_branch}/tip")

        # Create tags
        for tag_operation in tag_ops:
            if not self._commit_has_mercurial_metadata(
                repo, tag_operation.source_commit
            ):
                raise MercurialMetadataNotFoundError(tag_operation)
            try:
                repo.git.cinnabar(
                    [
                        "tag",
                        "--onto",
                        f"refs/heads/{tag_operation.tags_destination_branch}",
                        tag_operation.tag,
                        tag_operation.source_commit,
                    ],
                )
            except Exception as e:
                raise RepoSyncError(tag_operation, e) from e

        logger.debug(f"Push arguments: {push_args}")
        # Push commits, branches and tags to destination
        retry(
            "pushing branch and tags to destination",
            lambda: repo.git.push(*push_args),
        )
