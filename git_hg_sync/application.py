import dataclasses
import json
import signal
import sys
from collections.abc import Sequence
from types import FrameType

from mozlog import get_proxy_logger

from git_hg_sync.events import Push, Tag
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
            if self._worker.should_stop:
                logger.info("Process killed by user")
                sys.exit(1)
            self._worker.should_stop = True
            logger.info("Process exiting gracefully")

        signal.signal(signal.SIGINT, signal_handler)
        self._worker.run()

    def _handle_push_event(self, push_event: Push) -> None:
        logger.info(f"Handling push event: {push_event.pushid}")
        synchronizer = self._repo_synchronizers[push_event.repo_url]
        operations_by_destination: dict[str, list[SyncOperation]] = {}

        for mapping in self._mappings:
            if matches := mapping.match(push_event):
                for match in matches:
                    operations_by_destination.setdefault(
                        match.destination_url, []
                    ).append(match.operation)

        for destination, operations in operations_by_destination.items():
            # noinspection PyBroadException
            try:
                with retry(action="executing sync operations", tries=3, delay=5):
                    synchronizer.sync(destination, operations)
            except Exception:
                error_data = json.dumps(
                    {
                        "destination_url": destination,
                        "operations": [
                            dataclasses.asdict(operation) for operation in operations
                        ],
                    }
                )
                logger.error(
                    f"An error prevented completion of the following sync operations. {error_data}",
                    exc_info=True,
                )

    def _handle_event(self, event: Push | Tag) -> None:
        if event.repo_url not in self._repo_synchronizers:
            logger.info("Ignoring event for untracked repository: %()s", event.repo_url)
            return
        match event:
            case Push():
                self._handle_push_event(event)
            case _:
                raise NotImplementedError()
