from dataclasses import dataclass
from pathlib import Path

from git import Repo
from mozlog import get_proxy_logger

from git_hg_sync import config

logger = get_proxy_logger("sync_repo")
HERE = Path(__file__).parent


@dataclass
class Push:
    type: str
    repo_url: str
    heads: list[str]
    commits: list[str]
    time: int
    pushid: int
    user: str
    push_json_url: str


@dataclass
class Tag:
    type: str
    repo_url: str
    tag: str
    commit: str
    time: int
    pushid: int
    user: str
    push_json_url: str


def parse_entity(raw_entity):
    if raw_entity["type"] == "push":
        entity = Push(**raw_entity)
    elif raw_entity["type"] == "tag":
        entity = Tag(**raw_entity)
    else:
        raise AttributeError(f"unsupported type {raw_entity['type']}")
    return entity


def process(raw_entity):
    entity = parse_entity(raw_entity)
    repo_config = config.get_repos_config(HERE.parent / "repos.json").get(
        entity.repo_url
    )
    if not repo_config:
        logger.warning(f"repo {entity.repo_url} is not supported yet")
        return
    repo = Repo(repo_config["clone"])
    remote = repo.remote(repo_config["remote"])
    if entity.type == "push":
        # fetch new commits
        remote.fetch()
        # add commits to the good branch
        for commit_sha in entity.commits:
            logger.info(f"handle commit {commit_sha}")
            repo.git.cherry_pick(commit_sha)
        # push on good repo/branch
        remote = repo.remote(repo_config["target"])
        remote.push()
    elif entity.type == "tag":
        pass  # TODO
