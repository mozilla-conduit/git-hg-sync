import pathlib
import tomllib
from typing import Self

import pydantic


class PulseConfig(pydantic.BaseModel):
    userid: str
    host: str
    port: int
    exchange: str
    routing_key: str
    queue: str
    password: str


class TrackedRepository(pydantic.BaseModel):
    name: str
    url: str


class MappingSource(pydantic.BaseModel):
    url: str
    branch_pattern: str


class MappingDestination(pydantic.BaseModel):
    url: str
    branch: str


class Mapping(pydantic.BaseModel):
    source: MappingSource
    destination: MappingDestination


class ClonesConfig(pydantic.BaseModel):
    directory: pathlib.Path


class Config(pydantic.BaseModel):
    pulse: PulseConfig
    clones: ClonesConfig
    tracked_repositories: list[TrackedRepository]
    mappings: list[Mapping]

    @pydantic.model_validator(mode="after")
    def verify_all_mappings_reference_tracked_repositories(
        self,
    ) -> Self:
        tracked_urls = [tracked_repo.url for tracked_repo in self.tracked_repositories]
        for mapping in self.mappings:
            if mapping.source.url not in tracked_urls:
                raise ValueError(
                    f"Found mapping for untracked repository: {mapping.source.url}"
                )
        return self

    @staticmethod
    def from_file(file_path: pathlib.Path) -> "Config":
        assert file_path.exists(), f"config file {file_path} doesn't exists"
        with open(file_path, "rb") as config_file:
            config = tomllib.load(config_file)
        return Config(**config)
