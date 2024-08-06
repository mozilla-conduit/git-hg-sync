from pathlib import Path
from typing import Literal

from git import Repo
from mozlog import get_proxy_logger

from git_hg_sync.config import Mapping, TrackedRepository
from git_hg_sync.events import Push, Tag

logger = get_proxy_logger("sync_repo")


class RepoSynchronizer:

    def __init__(
        self,
        clones_directory: Path,
        tracked_repositories: list[TrackedRepository],
        mappings: list[Mapping],
    ):
        self._clones_directory = clones_directory
        self._tracked_repositories = tracked_repositories
        self._mappings = mappings

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

    def handle_commits(self, push_message: Push, clone_dir: Path, mapping: Mapping):
        logger.info(f"Handle entity {push_message.pushid}")
        assert Path(clone_dir).exists(), f"clone {clone_dir} doesn't exists"
        repo = Repo(clone_dir)
        remote = self.get_remote(repo, "git", mapping.source.url)
        # fetch new commits
        for branch_name, commit in push_message.branches.items():
            remote.fetch(commit)
            if branch_name in repo.branches:
                branch = repo.branches[branch_name]
                branch.commit = commit
            else:
                branch = repo.create_head(branch_name, commit)
            if mapping.source.branch_pattern == branch_name:
                remote = self.get_remote(repo, "hg", "hg::" + mapping.destination.url)
                remote.push(branch.name)

        # match push_message:
        #    case Push():
        #        for head in push_message.heads:
        #            remote.pull(head)
        #    case _:
        #        pass  # TODO
        ## push on good repo/branch
        # remote = self.get_remote(repo, "hg", "hg::" + mapping.rules.mercurial_repository)
        # remote.push(push_message.heads)
        # logger.info(f"Done for entity {push_message.pushid}")

    def sync(self, entity: Push | Tag) -> None:
        source_url = entity.repo_url
        if isinstance(entity, Tag):
            logger.warning("Tag message not handled not implemented yet")
            return

        matching_mappings = [
            mapping for mapping in self._mappings if mapping.source == entity.repo_url
        ]
        if not matching_mappings:
            logger.warning(f"No mapping found for git repository {entity.repo_url} ")
            return

        if len(matching_mappings) > 1:
            logger.warning(f"No mapping found for git repository {entity.repo_url} ")
            return

        mapping = matching_mappings[0]
        clone_name = next(
            tracked_repo.url
            for tracked_repo in self._tracked_repositories
            if tracked_repo.url == source_url
        )
        clone_directory = self._clones_directory / clone_name
        self.handle_commits(
            entity,
            clone_directory,
            mapping,
        )
