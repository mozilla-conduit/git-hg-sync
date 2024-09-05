from pathlib import Path
import subprocess


def hg_export_tip(repo_path: Path):
    process = subprocess.run(
        ["hg", "export", "tip"],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
    )
    return process.stdout
