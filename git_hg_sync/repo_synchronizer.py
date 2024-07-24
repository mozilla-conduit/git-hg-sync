from dataclasses import dataclass
from pathlib import Path

from git import Repo
from mozlog import get_proxy_logger

logger = get_proxy_logger("sync_repo")


class EntityTypeError(Exception):
    pass


@dataclass
class Push:
    repo_url: str
    heads: list[str]
    commits: list[str]
    time: int
    pushid: int
    user: str
    push_json_url: str


@dataclass
class Tag:
    repo_url: str
    tag: str
    commit: str
    time: int
    pushid: int
    user: str
    push_json_url: str


class RepoSynchronyzer:

    def __init__(self, repos_config):
        self._repos_config = repos_config

    def parse_entity(self, raw_entity):
        logger.debug(f"parse_entity: {raw_entity}")
        message_type = raw_entity.pop("type")
        match message_type:
            case "push":
                return Push(**raw_entity)
            case "tag":
                return Tag(**raw_entity)
            case _:
                raise EntityTypeError(f"unsupported type {message_type}")

    def get_remote(self, repo, remote_url):
        """
        get the repo if it exists, create it otherwise
        the repo name is the last part of the url
        """
        remote_name = remote_url.split("/")[-1]
        for rem in repo.remotes:
            if rem.name == remote_name:
                return repo.remote(remote_name)
                break
        else:
            return repo.create_remote(remote_name, remote_url)

    def handle_commits(self, entity, clone_dir, remote_url, remote_target):
        logger.info(f"Handle entity {entity.pushid}")
        assert Path(clone_dir).exists(), f"clone {clone_dir} doesn't exists"
        repo = Repo(clone_dir)
        remote = self.get_remote(repo, remote_url)
        # fetch new commits
        remote.fetch()
        match entity:
            case Push():
                remote.pull("branches/default/tip")
            case _:
                pass  # TODO
        # push on good repo/branch
        remote = repo.remote(remote_target)
        remote.push()
        logger.info(f"Done for entity {entity.pushid}")

    def sync(self, raw_entity):
        entity = self.parse_entity(raw_entity)
        repo_config = self._repos_config.get(entity.repo_url)
        if not repo_config:
            logger.warning(f"repo {entity.repo_url} is not supported yet")
            return
        self.handle_commits(
            entity, repo_config["clone"], entity.repo_url, repo_config["target"]
        )
