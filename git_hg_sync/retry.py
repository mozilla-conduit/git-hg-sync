from collections.abc import Callable
import time
from typing import TypeVar

from mozlog import get_proxy_logger

TResult = TypeVar("TResult")

logger = get_proxy_logger(__name__)


def retry(
    func: Callable[[], TResult], tries: int, action: str = "", delay: float = 0.0
) -> TResult:
    """
    Retry a function on failure.
    Args:
        func (Callable): The function to retry.
        tries (int): The number of attempts to make before failing.
        action (str): A description of the action being performed for better logging context (eg. "fetching commits")
        delay (float): The delay in seconds between attempts.

    Returns:
        _Ret: The return value of the function if successful.

    Raises:
        Exception: The last exception raised if all attempts fail.
    """
    for attempt in range(1, tries + 1):
        try:
            return func()
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

    assert False, "unreachable"
