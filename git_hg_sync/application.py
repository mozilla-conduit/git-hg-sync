import dataclasses
import json
import os
import signal
import sys
from collections.abc import Sequence
from functools import partial
from types import FrameType

from mozlog import get_proxy_logger

from git_hg_sync import PID_FILEPATH
from git_hg_sync.events import Event, Push
from git_hg_sync.mapping import Mapping, SyncOperation
from git_hg_sync.pulse_worker import PulseWorker
from git_hg_sync.repo_synchronizer import RepoSynchronizer
from git_hg_sync.retry import retry

logger = get_proxy_logger(__name__)


class Application:
    def __init__(
        self,
        worker: PulseWorker,
        repo_synchronizers: dict[str, RepoSynchronizer],
        mappings: Sequence[Mapping],
    ) -> None:
        self._worker = worker
        self._worker.event_handler = self._handle_event
        self._repo_synchronizers = repo_synchronizers
        self._mappings = mappings

    def run(self) -> None:
        def signal_handler(_sig: int, _frame: FrameType | None) -> None:
            PID_FILEPATH.unlink(missing_ok=True)
            if self._worker.should_stop:
                logger.info("Process killed by user")
                sys.exit(1)
            self._worker.should_stop = True
            logger.info("Process exiting gracefully")

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        PID_FILEPATH.write_text(f"{os.getpid()}\n")
        self._worker.run()

    def _handle_push_event(self, push_event: Push) -> None:
        logger.debug(
            f"Handling push event: {push_event.push_id} for {push_event.repo_url}"
        )
        synchronizer = self._repo_synchronizers[push_event.repo_url]
        operations_by_destination: dict[str, list[SyncOperation]] = {}

        for mapping in self._mappings:
            if matches := mapping.match(push_event):
                for match in matches:
                    operations_by_destination.setdefault(
                        match.destination_url, []
                    ).append(match.operation)

        if not operations_by_destination:
            logger.warning(f"No operation for {push_event}")
            return

        for destination, operations in operations_by_destination.items():
            try:
                retry(
                    "executing sync operations",
                    # Python gotcha: when creating closure in a loop, any loop
                    # variable used in the closure takes the last value of the variable,
                    # at the end of the loop [0].
                    #
                    # We can use functools.partial to early-bind those parameters into
                    # a Callable.
                    #
                    # [0] https://docs.python-guide.org/writing/gotchas/#late-binding-closures
                    partial(synchronizer.sync, destination, operations),
                    tries=3,
                    delay=5,
                )
            except Exception as exc:
                error_data = json.dumps(
                    {
                        "destination_url": destination,
                        "operations": [
                            dataclasses.asdict(operation) for operation in operations
                        ],
                    }
                )
                logger.warning(
                    f"An error prevented completion of the following sync operations. {error_data}",
                    exc_info=True,
                )
                raise exc
        logger.info(
            f"Successfully handled event: {push_event.push_id} for {push_event.repo_url}"
        )

    def _handle_event(self, event: Event) -> None:
        if event.repo_url not in self._repo_synchronizers:
            logger.warning(f"Ignoring event for untracked repository: {event.repo_url}")
            return
        match event:
            case Push():
                self._handle_push_event(event)
            case _:
                raise NotImplementedError()
