from pathlib import Path

from git import Repo

HERE = Path(__file__).parent


def git_cinnabar_process(entity):
    if entity.type != "push":
        print(f"{entity.type} type is not supported")
    repo = Repo(HERE.parent / "clones/chatzilla_cinnabar")
    for commit in reversed(entity.commits):
        print(commit)
        remote = repo.remote(entity.repo_url)
        remote.fetch(commit)
        repo.git.cherry_pick(commit)
        remote = repo.remote("origin")
        remote.push()
        print("done")
