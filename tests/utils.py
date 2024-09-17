from pathlib import Path
import subprocess


def hg_cat(repo_path: Path, file: Path | str, revision: str):
    process = subprocess.run(
        ["hg", "cat", str(file), "-r", revision],
        cwd=repo_path,
        capture_output=True,
        check=True,
        text=True,
    )
    return process.stdout
