import pathlib 
import tomllib
import json

import pydantic

class PulseConfig(pydantic.BaseModel):
    userid: str
    host: str
    port: int
    exchange: str
    routing_key: str
    queue: str
    password: str


class Config(pydantic.BaseModel):
    pulse: PulseConfig

    @staticmethod
    def from_file(file_path: pathlib.Path) -> "Config":
        assert file_path.exists(), f"config file {file_path} doesn't exists"
        with open(file_path, "rb") as config_file:
            config = tomllib.load(config_file)
        return Config(**config)


def get_repos_config(repo_file_path: pathlib.Path):
    assert repo_file_path.exists(), f"config file {repo_file_path} doesn't exists"
    with open(repo_file_path) as f:
        repos = json.load(f)
    return repos
