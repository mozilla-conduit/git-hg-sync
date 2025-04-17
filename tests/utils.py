import subprocess
from pathlib import Path


def hg_cat(repo_path: Path, file: Path | str, revision: str) -> str:
    return hg_run(repo_path, ["hg", "cat", str(file), "-r", revision])


def hg_rev(repo_path: Path, revision: str = ".") -> str:
    return hg_log(repo_path, revision, ["-T", "{node}"])


def hg_log(
    repo_path: Path, revision: str = ".", extra_args: list[str] | None = None
) -> str:
    args = ["hg", "log", "-r", revision]
    if extra_args:
        args.extend(extra_args)
    return hg_run(repo_path, args)


def hg_run(repo_path: Path, hg_args: list[str]) -> str:
    process = subprocess.run(
        hg_args,
        cwd=repo_path,
        capture_output=True,
        check=True,
        text=True,
    )
    return process.stdout
