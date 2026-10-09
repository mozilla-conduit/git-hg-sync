import logging

import pytest
from pytest import LogCaptureFixture

from git_hg_sync.logging import LoggerContext


def test_logger_context_success(caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    with LoggerContext("succeeding with extras") as logger_context:
        logger_context.set_extra("test", "should succeed")

    assert "succeeding with extras" in caplog.text
    assert "failed " not in caplog.text
    # extras are added as attributes on the LogCaptureFixture
    assert caplog.records[0].test == "should succeed"


def test_logger_context_failure(caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    with (
        pytest.raises(ValueError, match="catch that"),
        LoggerContext("succeeding with extras") as logger_context,
    ):
        logger_context.set_extra("test", "should fail")
        raise ValueError("catch that")

    assert "failed succeeding with extras" in caplog.text
    assert "catch that" in caplog.text
    assert caplog.records[0].test == "should fail"


def test_logger_context_failure_swallowed(caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    with LoggerContext(
        "succeeding with extras", swallow_exceptions=True
    ) as logger_context:
        logger_context.set_extra("test", "should fail silently")
        raise ValueError("swallow that")

    # This code is not actually unreachable, as the LoggerContext should swallow the
    # exception.
    assert "failed succeeding with extras" in caplog.text
    assert "swallow that" in caplog.text
    assert caplog.records[0].test == "should fail silently"
