import configparser
import json


def get_pulse_config(config_file_path):
    assert config_file_path.exists(), f"config file {config_file_path} doesn't exists"
    config = configparser.ConfigParser()
    config.read(config_file_path)
    return config


def get_repos_config(repo_file_path):
    assert repo_file_path.exists(), f"config file {repo_file_path} doesn't exists"
    with open(repo_file_path) as f:
        repos = json.load(f)
    return repos
