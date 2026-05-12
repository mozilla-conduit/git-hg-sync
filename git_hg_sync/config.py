import pathlib
from typing import Annotated, Self, override

import tomllib
from mozlog import get_proxy_logger
from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from git_hg_sync.mapping import BranchMapping, TagMapping

logger = get_proxy_logger(__name__)


class PulseConfig(BaseSettings):
    userid: str
    host: str
    port: int
    exchange: str
    routing_key: str
    queue: str
    password: str
    heartbeat: int
    ssl: bool


class TrackedRepository(BaseSettings):
    name: str
    url: str


class ClonesConfig(BaseSettings):
    directory: pathlib.Path


class SentryConfig(BaseSettings):
    sentry_dsn: Annotated[str, Field(alias=AliasChoices("sentry_dsn", "dsn"))] = ""


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="_",
        env_nested_max_split=1,
        nested_model_default_partial_update=True,
    )

    pulse: PulseConfig
    sentry: SentryConfig | None = None
    clones: ClonesConfig
    tracked_repositories: list[TrackedRepository]
    branch_mappings: list[BranchMapping]
    tag_mappings: list[TagMapping] = []

    @model_validator(mode="after")
    def verify_all_mappings_reference_tracked_repositories(
        self,
    ) -> Self:
        tracked_urls = [tracked_repo.url for tracked_repo in self.tracked_repositories]
        for mapping in self.branch_mappings:
            if mapping.source_url not in tracked_urls:
                raise ValueError(
                    f"Found mapping for untracked repository: {mapping.source_url}"
                )
        return self

    @override
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Settings sources so the environment takes precedence over init options."""
        return (
            env_settings,
            init_settings,
        )

    @staticmethod
    def from_file(file_path: pathlib.Path) -> "Config":
        assert file_path.exists(), f"config file {file_path} doesn't exists"
        if "config-suite.toml" in str(file_path):
            pytest.skip("ignoring placeholder file created by suite")
        with file_path.open("rb") as config_file:
            config = tomllib.load(config_file)
        return Config(**config)
