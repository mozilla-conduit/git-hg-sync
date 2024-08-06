from pathlib import Path
from typing import Literal

from git import Repo
from mozlog import get_proxy_logger

from git_hg_sync.config import MappingConfig
from git_hg_sync.events import Push, Tag

logger = get_proxy_logger("sync_repo")


class RepoSynchronyzer:

    def __init__(self, clones_directory: Path, mappings: dict[str, MappingConfig]):
        self._clones_directory = clones_directory
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

    def handle_commits(
        self, push_message: Push, clone_dir: Path, mapping: MappingConfig
    ):
        logger.info(f"Handle entity {push_message.pushid}")
        assert Path(clone_dir).exists(), f"clone {clone_dir} doesn't exists"
        repo = Repo(clone_dir)
        remote = self.get_remote(repo, "git", mapping.git_repository)
        # fetch new commits
        for branch_name, commit in push_message.branches.items():
            remote.fetch(commit)
            if branch_name in repo.branches:
                branch = repo.branches[branch_name]
                branch.commit = commit
            else:
                branch = repo.create_head(branch_name, commit)
            for rule_name, rule in mapping.rules.items():
                if rule.branch_pattern == branch_name:
                    remote = self.get_remote(
                        repo, "hg", "hg::" + rule.mercurial_repository
                    )
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
        if isinstance(entity, Tag):
            logger.warning("Tag message not handled not implemented yet")
            return

        matching_mappings = [
            (mapping_name, mapping)
            for mapping_name, mapping in self._mappings.items()
            if mapping.git_repository == entity.repo_url
        ]
        if not matching_mappings:
            logger.warning(f"No mapping found for git repository {entity.repo_url} ")
            return

        if len(matching_mappings) > 1:
            logger.warning(f"No mapping found for git repository {entity.repo_url} ")
            return

        mapping_name, mapping = matching_mappings[0]
        clone_directory = self._clones_directory / mapping_name
        self.handle_commits(
            entity,
            clone_directory,
            mapping,
        )
