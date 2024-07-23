from dataclasses import dataclass
from pathlib import Path

from git import Repo
from mozlog import get_proxy_logger

from git_hg_sync import config

logger = get_proxy_logger("sync_repo")
HERE = Path(__file__).parent


class EntityTypeError(Exception):
    pass


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
    logger.debug(f"parse_entity: {raw_entity}")
    if raw_entity["type"] == "push":
        entity = Push(**raw_entity)
    elif raw_entity["type"] == "tag":
        entity = Tag(**raw_entity)
    else:
        raise EntityTypeError(f"unsupported type {raw_entity['type']}")
    return entity


def get_remote(repo, remote_url):
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


def handle_commits(entity, clone_dir, remote_url, remote_target):
    logger.info(f"Handle entity {entity.pushid}")
    assert Path(clone_dir).exists(), f"clone {clone_dir} doesn't exists"
    repo = Repo(clone_dir)
    remote = get_remote(repo, remote_url)
    # fetch new commits
    remote.fetch()
    if entity.type == "push":
        remote.pull("branches/default/tip")
    elif entity.type == "tag":
        repo.commit(entity.commit)
        repo.create_tag(entity.tag)
    # push on good repo/branch
    remote = repo.remote(remote_target)
    remote.push()
    logger.info(f"Done for entity {entity.pushid}")


def process(raw_entity):
    entity = parse_entity(raw_entity)
    repo_config = config.get_repos_config(HERE.parent / "repos.json").get(
        entity.repo_url
    )
    if not repo_config:
        logger.warning(f"repo {entity.repo_url} is not supported yet")
        return
    handle_commits(entity, repo_config["clone"], entity.repo_url, repo_config["target"])
