import pytest
import mozlog


@pytest.fixture(autouse=True)
def mozlog_logging():
    logger = mozlog.structuredlog.StructuredLogger("tests")
    mozlog.structuredlog.set_default_logger(logger)
