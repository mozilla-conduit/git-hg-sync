import os
import pathlib
from typing import Self

import pydantic
import tomllib

from git_hg_sync.mapping import BranchMapping, TagMapping


class PulseConfig(pydantic.BaseModel):
    userid: str
    host: str
    port: int
    exchange: str
    routing_key: str
    queue: str
    password: str
    ssl: bool


class TrackedRepository(pydantic.BaseModel):
    name: str
    url: str


class ClonesConfig(pydantic.BaseModel):
    directory: pathlib.Path


class SentryConfig(pydantic.BaseModel):
    sentry_url: str | None = None


class Config(pydantic.BaseModel):
    pulse: PulseConfig
    sentry: SentryConfig | None = None
    clones: ClonesConfig
    tracked_repositories: list[TrackedRepository]
    branch_mappings: list[BranchMapping]
    tag_mappings: list[TagMapping]

    @pydantic.model_validator(mode="after")
    def verify_all_mappings_reference_tracked_repositories(
        self,
    ) -> Self:
        # Allow to override Pulse parameters via environment.
        for config in self.pulse.model_fields:
            env_var = f"PULSE_{config}".upper()
            if value := os.getenv(env_var):
                setattr(self.pulse, config, value)

        tracked_urls = [tracked_repo.url for tracked_repo in self.tracked_repositories]
        for mapping in self.branch_mappings:
            if mapping.source_url not in tracked_urls:
                raise ValueError(
                    f"Found mapping for untracked repository: {mapping.source_url}"
                )
        return self

    @staticmethod
    def from_file(file_path: pathlib.Path) -> "Config":
        assert file_path.exists(), f"config file {file_path} doesn't exists"
        with file_path.open("rb") as config_file:
            config = tomllib.load(config_file)
        return Config(**config)
