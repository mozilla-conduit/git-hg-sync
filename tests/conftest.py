import mozlog
import pytest

from git_hg_sync.config import PulseConfig


@pytest.fixture(autouse=True)
def mozlog_logging():
    logger = mozlog.structuredlog.StructuredLogger("tests")
    mozlog.structuredlog.set_default_logger(logger)


@pytest.fixture
def pulse_config():
    return PulseConfig(
        **{
            "userid": "guest",
            "host": "pulse",
            "port": 5672,
            "exchange": "exchange/guest/test",
            "routing_key": "#",
            "queue": "queue/guest/test",
            "password": "guest",
            "ssl": False,
        }
    )
