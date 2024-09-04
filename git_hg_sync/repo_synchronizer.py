from dataclasses import dataclass
from pathlib import Path
from typing import Literal


from git import Remote, Repo, exc
from git_hg_sync.mapping import SyncOperation, SyncBranchOperation, SyncTagOperation
from mozlog import get_proxy_logger

logger = get_proxy_logger("sync_repo")


@dataclass
class RefSpec:
    source: str
    destination: str


class RepoSynchronizer:

    def __init__(
        self,
        clone_directory: Path,
        url: str,
    ):
        self._clone_directory = clone_directory
        self._url = url

    def _get_clone_repo(self) -> Repo:
        if self._clone_directory.exists():
            return Repo(self._clone_directory)

        repo = Repo.init(self._clone_directory)
        with repo.config_writer() as config:
            config.add_section("cinnabar")
            config.set("cinnabar", "experiments", "branch,tag,git_commit,merge")
        return repo

    def get_remote(
        self, repo: Repo, remote_name: Literal["git", "hg"], remote_url: str
    ) -> Remote:
        """
        get the repo if it exists, create it otherwise
        the repo name is the last part of the url
        """
        for rem in repo.remotes:
            if rem.name == remote_name:
                remote = repo.remote(remote_name)
                remote.set_url(remote_url, allow_unsafe_protocols=True)
                return remote
        else:
            return repo.create_remote(
                remote_name, remote_url, allow_unsafe_protocols=True
            )

    def sync(self, destination_url: str, operations: list[SyncOperation]) -> None:
        # Ensure we have all commits from destination repository
        repo = self._get_clone_repo()
        try:
            repo.git.fetch(["hg::" + destination_url])
        except exc.GitCommandError as e:
            # can't fetch if repo is empty
            if "fatal: couldn't find remote ref HEAD" not in e.stderr:
                raise e
        remote = self.get_remote(repo, "git", self._url)

        # Get commits we want to send to destination repository
        commits_to_fetch = [operation.source_commit for operation in operations]
        repo.git.fetch([remote.name, *commits_to_fetch])

        # Push commits, branches and tags to destination
        push_args = ["hg::" + destination_url]
        for operation in operations:
            match operation:
                case SyncBranchOperation():
                    push_args.append(
                        f"{operation.source_commit}:refs/heads/branches/{operation.destination_branch}/tip"
                    )
                case SyncTagOperation():
                    # TODO
                    raise NotImplementedError()
        repo.git.push(*push_args)
