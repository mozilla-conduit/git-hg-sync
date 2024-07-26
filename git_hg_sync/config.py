import pathlib
import tomllib
from collections import Counter

import pydantic


class PulseConfig(pydantic.BaseModel):
    userid: str
    host: str
    port: int
    exchange: str
    routing_key: str
    queue: str
    password: str


class MappingRule(pydantic.BaseModel):
    branch_pattern: str
    mercurial_repository: str


class MappingConfig(pydantic.BaseModel):
    git_repository: str
    rules: dict[str, MappingRule]


class ClonesConfig(pydantic.BaseModel):
    directory: pathlib.Path


class Config(pydantic.BaseModel):
    pulse: PulseConfig
    clones: ClonesConfig
    mappings: dict[str, MappingConfig]

    @pydantic.field_validator("mappings")
    @staticmethod
    def no_duplicate_git_repositories(
        mappings: dict[str, MappingConfig]
    ) -> dict[str, MappingConfig]:
        counter = Counter([mapping.git_repository for mapping in mappings.values()])
        for git_repo, count in counter.items():
            if count > 1:
                raise ValueError(
                    f"Found {count} different mappings for the same git repository."
                )
        return mappings

    @staticmethod
    def from_file(file_path: pathlib.Path) -> "Config":
        assert file_path.exists(), f"config file {file_path} doesn't exists"
        with open(file_path, "rb") as config_file:
            config = tomllib.load(config_file)
        return Config(**config)
