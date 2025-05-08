import os
import pathlib
from typing import Self

import pydantic
import tomllib
from mozlog import get_proxy_logger

from git_hg_sync.mapping import BranchMapping, TagMapping

logger = get_proxy_logger(__name__)


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
    sentry_dsn: str | None = None


class Config(pydantic.BaseModel):
    pulse: PulseConfig
    sentry: SentryConfig = SentryConfig(sentry_dsn="")
    clones: ClonesConfig
    tracked_repositories: list[TrackedRepository]
    branch_mappings: list[BranchMapping]
    tag_mappings: list[TagMapping] = []

    @pydantic.model_validator(mode="after")
    def verify_all_mappings_reference_tracked_repositories(
        self,
    ) -> Self:
        for config_field in PulseConfig.model_fields:
            env_var = f"PULSE_{config_field}".upper()
            self._update_config_from_env(
                f"Pulse {config_field}", self.pulse, config_field, env_var
            )

        self._update_config_from_env(
            "Sentry DSN", self.sentry, "sentry_dsn", "SENTRY_DSN"
        )

        tracked_urls = [tracked_repo.url for tracked_repo in self.tracked_repositories]
        for mapping in self.branch_mappings:
            if mapping.source_url not in tracked_urls:
                raise ValueError(
                    f"Found mapping for untracked repository: {mapping.source_url}"
                )
        return self

    @staticmethod
    def _update_config_from_env(
        name: str,
        config_entry: pydantic.BaseModel | None,
        config_field: str,
        env_var: str,
    ) -> None:
        """Update a specific field in a model based on the environment."""
        if not config_entry:
            return

        if value := os.getenv(env_var):
            logger.info(f"Setting {name} option from {env_var}")
            setattr(config_entry, config_field, value)

    @staticmethod
    def from_file(file_path: pathlib.Path) -> "Config":
        assert file_path.exists(), f"config file {file_path} doesn't exists"
        with file_path.open("rb") as config_file:
            config = tomllib.load(config_file)
        return Config(**config)
