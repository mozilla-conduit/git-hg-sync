import logging

from git import Repo

from git_hg_sync import config

logger = logging.getLogger()


def git_cinnabar_process(entity):
    if entity.type != "push":
        logger.warning(f"{entity.type} type is not supported")
    repo_config = config.get_repos_config().get(entity.repo_url)
    if not repo_config:
        logger.warning(f"repo {entity.repo_url} is not supported yet")
    else:
        repo = Repo(repo_config["clone"])
        for commit in reversed(entity.commits):
            logger.debug(commit)
            remote = repo.remote(entity.repo_url)
            remote.fetch(commit)
            repo.git.cherry_pick(commit)
            remote = repo.remote(repo_config["remote"])
            remote.push()
