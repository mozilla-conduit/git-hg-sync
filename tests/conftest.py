import sys
from collections.abc import Callable
from pathlib import Path

import mozlog
import mozlog.formatters
import mozlog.handlers
import pytest

from git_hg_sync.config import ClonesConfig, Config, PulseConfig, TrackedRepository
from git_hg_sync.mapping import BranchMapping


@pytest.fixture(autouse=True, scope="session")
def mozlog_logging() -> None:
    logger = mozlog.structuredlog.StructuredLogger("tests")
    logger.add_handler(
        mozlog.handlers.StreamHandler(sys.stdout, mozlog.formatters.JSONFormatter())
    )
    mozlog.structuredlog.set_default_logger(logger)


@pytest.fixture
def pulse_config() -> PulseConfig:
    return PulseConfig(
        userid="guest",
        host="pulse",
        port=5672,
        exchange="exchange/guest/test",
        routing_key="#",
        queue="queue/guest/test",
        password="guest",
        heartbeat=30,
        ssl=False,
    )

@pytest.fixture
def test_config(pulse_config: PulseConfig) -> Config:
    return Config(
        pulse=pulse_config,
        clones=ClonesConfig(directory=Path("clones")),
        tracked_repositories=[
            TrackedRepository(name="mozilla-central", url="https://github.com/mozilla-firefox/firefox.git"),
        ],
        branch_mappings=[BranchMapping(
            branch_pattern = '.*',
            source_url = "https://github.com/mozilla-firefox/firefox.git",
            destination_url = 'destination_url',
            destination_branch  = 'destination_branch',
        )],
    )

@pytest.fixture
def get_payload() -> Callable:

    def get_payload(**kwargs: dict) -> dict:
        """Return a default payload, with override via kwargs."""
        payload = {
            "type": "push",
            "repo_url": "repo.git",
            "branches": { "main": 40 * "0"},
            "tags": {},
            "time": 0,
            "push_id": 0,
            "user": "user",
            "push_json_url": "push_json_url",
        }
        payload.update(kwargs)
        return payload

    return get_payload
