import logging
from pathlib import Path

from git import Repo

HERE = Path(__file__).parent
GIT_CINNABAR_CLONE = HERE.parent / "clones/chatzilla_cinnabar"
logger = logging.getLogger()


def git_cinnabar_process(entity):
    if entity.type != "push":
        logger.warning(f"{entity.type} type is not supported")
    repo = Repo(GIT_CINNABAR_CLONE)
    for commit in reversed(entity.commits):
        logger.debug(commit)
        remote = repo.remote(entity.repo_url)
        remote.fetch(commit)
        repo.git.cherry_pick(commit)
        remote = repo.remote("origin")
        remote.push()
