import sys

import mozlog
import mozlog.formatters
import mozlog.handlers
import pytest

from git_hg_sync.config import PulseConfig


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
        ssl=False,
    )
