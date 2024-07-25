import mozlog
import pytest


@pytest.fixture(autouse=True)
def mozlog_logging():
    logger = mozlog.structuredlog.StructuredLogger("tests")
    mozlog.structuredlog.set_default_logger(logger)
