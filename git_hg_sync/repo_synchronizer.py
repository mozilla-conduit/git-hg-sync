from pathlib import Path

from git import Repo, exc
from mozlog import get_proxy_logger

from git_hg_sync.mapping import SyncBranchOperation, SyncOperation, SyncTagOperation

logger = get_proxy_logger("sync_repo")


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
            if "fatal: couldn't find remote ref HEAD" not in e.stderr:
                raise e

    def sync(self, destination_url: str, operations: list[SyncOperation]) -> None:
        repo = self._get_clone_repo()
        destination_remote = f"hg::{destination_url}"

        # Ensure we have all commits from destination repository
        self._fetch_all_from_remote(repo, destination_remote)

        # Get commits we want to send to destination repository
        commits_to_fetch = [operation.source_commit for operation in operations]
        repo.git.fetch([self._src_remote, *commits_to_fetch])

        push_args = [destination_remote]

        # Handle branch operations
        branch_ops: list[SyncBranchOperation] = [
            op for op in operations if isinstance(op, SyncBranchOperation)
        ]
        for branch_operation in branch_ops:
            push_args.append(
                f"{branch_operation.source_commit}:refs/heads/branches/{branch_operation.destination_branch}/tip"
            )

        # Add mercurial metadata to new commits from synced branches
        # Some of these commits could be tagged in the same synchronization and
        # tagging can only be done on a commit that already have mercurial
        # metadata
        if branch_ops:
            repo.git.execute(
                ["git", "-c", "cinnabar.data=force", "push", "--dry-run", *push_args]
            )

        # Handle tag operations
        tag_ops: list[SyncTagOperation] = [
            op for op in operations if isinstance(op, SyncTagOperation)
        ]

        # Create tag branches locally
        tag_branches = {op.tags_destination_branch for op in tag_ops}
        for tag_branch in tag_branches:
            repo.git.fetch(
                [
                    "-f",
                    destination_remote,
                    f"refs/heads/branches/{tag_branch}/tip:{tag_branch}",
                ]
            )
            push_args.append(f"{tag_branch}:refs/heads/branches/{tag_branch}/tip")

        # Create tags
        for tag_operation in tag_ops:
            if not self._commit_has_mercurial_metadata(
                repo, tag_operation.source_commit
            ):
                raise MercurialMetadataNotFoundError()
            repo.git.cinnabar(
                [
                    "tag",
                    "--onto",
                    f"refs/heads/{tag_operation.tags_destination_branch}",
                    tag_operation.tag,
                    tag_operation.source_commit,
                ]
            )

        # Push commits, branches and tags to destination
        repo.git.push(*push_args)
