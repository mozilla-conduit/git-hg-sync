import json
from dataclasses import asdict
from pathlib import Path


from git import Repo, exc
from git_hg_sync.mapping import SyncOperation, SyncBranchOperation, SyncTagOperation
from mozlog import get_proxy_logger


logger = get_proxy_logger(__name__)


class RepoSyncError(Exception):
    """Base exception class for git to mercurial synchronization errors"""


class MercurialMetadataNotFoundError(RepoSyncError):
    """Raised when a commit is not found"""


class RepoSynchronizer:
    def __init__(
        self,
        clone_directory: Path,
        url: str,
    ):
        self._clone_directory = clone_directory
        self._src_remote = url

    def _repo_config_as_dict(self, repo: Repo):
        with repo.config_reader() as reader:
            return {
                section: dict(reader.items(section)) for section in reader.sections()
            }

    def _get_clone_repo(self) -> Repo:
        """Get a GitPython Repo object pointing to a git clone of the source
        remote."""
        log_data = json.dumps({"clone_directory": str(self._clone_directory)})
        if self._clone_directory.exists():
            logger.debug(f"Clone directory exists. Using it .{log_data}")
            repo = Repo(self._clone_directory)
        else:
            logger.debug(f"Clone directory does not exist. Creating it. {log_data}")
            repo = Repo.init(self._clone_directory)

        # Ensure that the clone repository is well configured
        with repo.config_writer() as config:
            config.add_section("cinnabar")
            config.set("cinnabar", "experiments", "branch,tag,git_commit,merge")
        return repo

    def _commit_has_mercurial_metadata(self, repo: Repo, git_commit: str) -> bool:
        stdout = repo.git.cinnabar(["git2hg", git_commit])
        return not all([char == "0" for char in stdout.strip()])

    def _fetch_all_from_remote(self, repo: Repo, remote: str) -> None:
        try:
            repo.git.fetch([remote])
        except exc.GitCommandError as e:
            # can't fetch if repo is empty
            if "fatal: couldn't find remote ref HEAD" in e.stderr:
                return
            raise

    def _log_data(self, **kwargs):
        return json.dumps(
            {
                "clone_directory": str(self._clone_directory),
                "source_remote": self._src_remote,
                **kwargs,
            }
        )

    def sync(self, destination_url: str, operations: list[SyncOperation]) -> None:
        destination_remote = f"hg::{destination_url}"

        json_operations = self._log_data(
            destination_remote=destination_remote,
            operations=[asdict(op) for op in operations],
        )
        logger.info(f"Synchronizing. {json_operations}")

        repo = self._get_clone_repo()

        logger.debug(
            f"Git clone configuration. {self._log_data(configuration=self._repo_config_as_dict(repo))}"
        )

        # Ensure we have all commits from destination repository
        logger.debug(f"Fetching all commits from destination. {self._log_data()}")
        self._fetch_all_from_remote(repo, destination_remote)

        # Get commits we want to send to destination repository
        commits_to_fetch = [operation.source_commit for operation in operations]
        logger.debug(
            f"Fetching source commits. {self._log_data(commits=commits_to_fetch)}"
        )
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
            logger.debug(
                f"Adding mercurial metadata to git commits. {self._log_data(args=push_args)}"
            )
            repo.git.execute(
                ["git", "-c", "cinnabar.data=force", "push", "--dry-run", *push_args]
            )

        # Handle tag operations
        tag_ops: list[SyncTagOperation] = [
            op for op in operations if isinstance(op, SyncTagOperation)
        ]

        # Create tag branches locally
        tag_branches = set([op.tags_destination_branch for op in tag_ops])
        for tag_branch in tag_branches:
            logger.debug(
                f"Get tag branch from destination. {self._log_data(tag_branch=tag_branch)}."
            )
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
            commit_has_metadata = self._commit_has_mercurial_metadata(
                repo, tag_operation.source_commit
            )
            if not commit_has_metadata:
                raise MercurialMetadataNotFoundError()
            logger.debug(
                f"Creating tag. {self._log_data(operation=asdict(tag_operation))}"
            )
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
        logged_command = ["git", "push", *push_args]
        logger.debug(
            f"Pushing branches and tags to destination. {self._log_data(command=logged_command)}"
        )
        repo.git.push(*push_args)
