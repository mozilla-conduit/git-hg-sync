import time
from collections.abc import Callable

from mozlog import get_proxy_logger

logger = get_proxy_logger("retry")


def retry(
    action: str,
    callback: Callable,
    *,
    tries: int = 2,
    delay: float = 0.25,
) -> None:
    """Run a `callback` up to `tries` times with a `delay` between Exceptions."""
    logger.debug(action)
    for attempt in range(1, tries + 1):
        try:
            callback()
            break
        except Exception as exc:
            action_text = f" {action}" if action else ""
            if attempt < tries:
                logger.error(
                    f"Failed attempt{action_text} [{attempt}/{tries}]. Retrying..."
                )
                if delay > 0:
                    time.sleep(delay)
            else:
                logger.error(
                    f"Final attempt{action_text} [{attempt}/{tries}] failed with error: {type(exc).__name__}: {exc}. Aborting.",
                    exc_info=True,
                )
                raise
