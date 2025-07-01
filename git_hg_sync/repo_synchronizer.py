import os
from functools import partial
from pathlib import Path

from git import Repo, exc
from mozlog import get_proxy_logger

from git_hg_sync.mapping import SyncBranchOperation, SyncOperation, SyncTagOperation
from git_hg_sync.retry import retry

logger = get_proxy_logger("sync_repo")

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

    def get_clone_repo(self) -> Repo:
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
        return not all(char == "0" for char in self._git2hg(repo, git_commit))

    def fetch_all_from_remote(self, repo: Repo, remote: str) -> None:
        try:
            repo.git.execute(["git", "-c", "cinnabar.graft=true", "fetch", remote])
        except exc.GitCommandError as e:
            # can't fetch if repo is empty
            if "fatal: couldn't find remote ref HEAD" in e.stderr:
                raise e

    def sync(
        self, destination_url: str, operations: list[SyncOperation], request_user: str
    ) -> None:
        logger.info(f"Syncing {operations} to {destination_url} ...")
        try:
            repo = self.get_clone_repo()
        except PermissionError as exc:
            raise PermissionError(
                f"Failed to create local clone from {destination_url}"
            ) from exc

        destination_remote = f"hg::{destination_url}"

        self._ensure_cinnabar_metadata(repo, destination_remote)

        # Get commits we want to send to destination repository
        commits_to_fetch = [operation.source_commit for operation in operations]
        retry(
            "fetching source commits",
            lambda: repo.git.fetch([self._src_remote, *commits_to_fetch]),
        )
        refs_to_push = []

        # Handle branch operations
        branch_ops: list[SyncBranchOperation] = [
            op for op in operations if isinstance(op, SyncBranchOperation)
        ]
        for branch_operation in branch_ops:
            try:
                refs_to_push.append(
                    branch_operation.source_commit
                    + ":"
                    + self._cinnabar_branch(branch_operation.destination_branch)
                )
            except Exception as e:
                raise RepoSyncError(branch_operation, e) from e

        os.environ[REQUEST_USER_ENV_VAR] = request_user
        os.environ["GIT_AUTHOR_EMAIL"] = request_user
        # We don't have the author name in the Pulse message, so we guess from the email
        # address.
        userinfo = request_user
        if "@" in userinfo:
            userinfo, _ = request_user.split("@")
        os.environ["GIT_AUTHOR_NAME"] = userinfo
        logger.debug(f"{REQUEST_USER_ENV_VAR} and GIT_AUTHOR_* set to {request_user}")

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
                    + [destination_remote]
                    + refs_to_push,
                ),
            )

        # Handle tag operations
        tag_ops: list[SyncTagOperation] = [
            op for op in operations if isinstance(op, SyncTagOperation)
        ]

        tags = repo.git.cinnabar(["tag", "--list"])

        # Create tags
        tag_branches_to_push = set()
        for tag_operation in tag_ops:
            if tag_operation.tag in tags:
                logger.warning(
                    f"Tag {tag_operation.tag} already exists in Cinnabar, skipping ..."
                )
                continue

            if not self._commit_has_mercurial_metadata(
                repo, tag_operation.source_commit
            ):
                raise MercurialMetadataNotFoundError(tag_operation)

            hg_sha = self._git2hg(repo, tag_operation.source_commit)
            tag_message = f"No bug - Tagging {hg_sha} with {tag_operation.tag} {tag_operation.tag_message_suffix}"
            try:
                repo.git.cinnabar(
                    [
                        "tag",
                        "--message",
                        tag_message,
                        "--onto",
                        f"refs/heads/{tag_operation.tags_destination_branch}",
                        tag_operation.tag,
                        tag_operation.source_commit,
                    ],
                )
            except Exception as e:
                raise RepoSyncError(tag_operation, e) from e

            tag_branches_to_push.add(tag_operation.tags_destination_branch)

        for tag_branch in tag_branches_to_push:
            refs_to_push.append(f"{tag_branch}:refs/heads/branches/{tag_branch}/tip")

        if not refs_to_push:
            logger.warning(
                "No explicit references to push resulted from processing this message."
            )
            return

        logger.debug(f"References to push: {refs_to_push}")

        for ref in refs_to_push:
            # Push commits, branches and tags to destination
            push_args = [destination_remote, ref]
            logger.debug(f"Push arguments: {push_args}")
            retry(
                f"pushing ref to destination {ref}",
                partial(repo.git.push, push_args),
            )

    def _ensure_cinnabar_metadata(self, repo: Repo, destination_remote: str) -> None:
        """Ensure we have all commits from destination repository.

        This sets up the correct cinnabar hg2git/git2hg mappings (including
        cinnabar.graft support).
        """

        # This is needed only on first initialisation of the repository, as subsequent
        # pushes update the metadata locally.

        # Repo.git_dir is a PathLike union which is either a str, or a smarter thing. We
        # assume the less smart one.
        cinnabar_metadata_dir = Path(repo.git_dir) / "refs/cinnabar/metadata"
        if cinnabar_metadata_dir.exists():
            logger.debug(
                f"Cinnabar metadata already present in  {cinnabar_metadata_dir}, not updating"
            )
            return

        retry(
            "fetching commits from destination",
            lambda: self.fetch_all_from_remote(repo, destination_remote),
        )

    def _git2hg(self, repo: Repo, git_commit: str) -> str:
        return repo.git.cinnabar(["git2hg", git_commit]).strip()

    def _cinnabar_branch(self, branch: str) -> str:
        return f"refs/heads/branches/{branch}/tip"
