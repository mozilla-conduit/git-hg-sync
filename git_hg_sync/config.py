import configparser
import json
from pathlib import Path

HERE = Path(__file__).parent


def get_pulse_config():
    config = configparser.ConfigParser()
    config.read(HERE.parent / "config.ini")
    return config


def get_repos_config():
    with open(HERE.parent / "repos.json") as f:
        repos = json.load(f)
    return repos


if __name__ == "__main__":
    get_pulse_config()
