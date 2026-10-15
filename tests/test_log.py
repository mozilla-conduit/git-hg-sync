import json
import logging
import sys

from git_hg_sync.log import MozLogFormatter


def _record(
    msg: str,
    level: int = logging.INFO,
    exc_info: logging._SysExcInfoType | None = None,
) -> logging.LogRecord:
    return logging.LogRecord(
        name="git_hg_sync.test",
        level=level,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=(),
        exc_info=exc_info,
    )


def test_format() -> None:
    record = _record("hello %s")
    record.args = ("world",)
    record.extra_field = 42

    data = json.loads(MozLogFormatter().format(record))

    assert data["action"] == "log"
    assert data["level"] == "INFO"
    assert data["message"] == "hello world"
    assert data["source"] == "git_hg_sync.test"
    assert data["Type"] == "git_hg_sync.test"
    assert data["Logger"] == "git-hg-sync"
    assert data["Severity"] == MozLogFormatter.SL_INFO
    assert data["Fields"] == {"extra_field": "42", "msg": "hello world"}


def test_format_exception() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        record = _record("failed", level=logging.ERROR, exc_info=sys.exc_info())

    data = json.loads(MozLogFormatter().format(record))

    assert data["Severity"] == MozLogFormatter.SL_ERR
    assert data["Fields"]["exc"]["error"] == "ValueError('boom')"
    assert "raise ValueError" in data["Fields"]["exc"]["traceback"]
