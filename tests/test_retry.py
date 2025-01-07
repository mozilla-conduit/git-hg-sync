import unittest.mock as mock
from typing import Literal, Never

import pytest
from git_hg_sync.retry import retry, logger


def test_retry_does_not_log_error_on_immediate_success():
    def true_on_first_call():
        return True

    with mock.patch.object(logger, "error", wraps=logger.error) as error_spy:
        assert retry(true_on_first_call, tries=2) is True

        error_spy.assert_not_called()


def test_retry_logs_error_on_first_failing_try():
    count = 0

    def true_on_second_call() -> Literal[True]:
        nonlocal count
        if count == 0:
            count += 1
            raise Exception("Error on first call")
        return True

    with mock.patch.object(logger, "error", wraps=logger.error) as error_spy:
        assert retry(true_on_second_call, tries=2) is True
        assert "Retrying" in error_spy.call_args.args[0]


def test_retry_abort_on_failing_last_try():
    def always_raising() -> Never:
        raise Exception("Error on first call")

    with mock.patch.object(logger, "error", wraps=logger.error) as error_spy:
        with pytest.raises(Exception):
            retry(always_raising, tries=2)

        assert "Aborting" in error_spy.call_args.args[0]


def test_retry_raises_inner_exception_on_last_failure():
    count = 0

    class MyCustomError(Exception):
        pass

    def always_raising():
        nonlocal count
        count += 1
        raise MyCustomError(f"Called {count} times")

    with pytest.raises(MyCustomError) as exc_info:
        retry(always_raising, tries=3)

    assert exc_info.value.args[0] == "Called 3 times"


def test_retry_shows_action_on_failed_attempt(caplog):

    def always_raising():
        raise ValueError("Commits too old")

    with mock.patch.object(logger, "error", wraps=logger.error) as error_spy:
        with pytest.raises(ValueError):
            retry(always_raising, tries=2, action="fetching old commits")

    assert "while fetching old commits" in error_spy.call_args.args[0]
