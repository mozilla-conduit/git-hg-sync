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
    """Run a `callback` up to `tries` times with a `delay` between Exceptions.

    The `callback` can be a closure built from a lambda function if needed.

        retry(
            "fetching commits from destination",
            lambda: self.fetch_all_from_remote(repo, destination_remote),
        )

    When using this method in a loop, and loop variables are used as part of the
    callback, an issue will arise due late-binding closures [0]. The `functools.partial`
    function can be used to properly bind the arguments.

        from functools import partial

        ...

        for ref in refs_to_push:
            retry(
                "pushing branch and tags to destination",
                partial(repo.git.push, [destination_remote, ref]),
            )

    [0] https://docs.python-guide.org/writing/gotchas/#late-binding-closures
    """
    logger.debug(action)
    for attempt in range(1, tries + 1):
        try:
            callback()
            break
        except Exception as exc:
            action_text = f" {action}" if action else ""
            if attempt < tries:
                logger.warning(
                    f"Failed attempt{action_text} [{attempt}/{tries}] failed with error: {type(exc).__name__}: {exc}. Retrying..."
                )
                if delay > 0:
                    time.sleep(delay)
            else:
                logger.error(
                    f"Final attempt{action_text} [{attempt}/{tries}] failed with error: {type(exc).__name__}: {exc}. Aborting.",
                    exc_info=True,
                )
                raise
