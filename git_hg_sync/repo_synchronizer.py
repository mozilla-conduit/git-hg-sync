from pathlib import Path
from typing import Literal
from dataclasses import dataclass

from git import Repo
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
        else:
            return Repo.init(self._clone_directory)

    def get_remote(self, repo, remote_name: Literal["git", "hg"], remote_url: str):
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

    def sync_branches(
        self, destination_url: str, refspecs: list[tuple[str, str]]
    ) -> None:
        repo = self._get_clone_repo()
        remote = self.get_remote(repo, "git", self._url)
        remote.fetch([refspec[0] for refspec in refspecs])
        push_args = ["hg::" + destination_url]
        push_args.extend(
            [
                f"{refspec[0]}:refs/heads/branches/{refspec[1]}/tip"
                for refspec in refspecs
            ]
        )
        repo.git.push(*push_args)
