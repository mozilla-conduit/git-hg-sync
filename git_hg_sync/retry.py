import contextlib
import time
from collections.abc import Generator
from typing import Any

from mozlog import get_proxy_logger

logger = get_proxy_logger("retry")


@contextlib.contextmanager
def retry(
    action: str,
    *,
    tries: int = 2,
    delay: float = 0.25,
) -> Generator[Any, None, None]:
    logger.debug(action)
    for attempt in range(1, tries + 1):
        try:
            yield
            break
        except Exception as exc:
            action_text = f" while {action}" if action else ""
            if attempt < tries:
                logger.error(
                    f"Attempt {attempt}/{tries} failed{action_text} with error: {type(exc).__name__}: {exc}. Retrying...",
                    exc_info=True,
                )
                if delay > 0:
                    time.sleep(delay)
            else:
                logger.error(
                    f"Attempt {attempt}/{tries} failed{action_text}. Aborting."
                )
                raise
