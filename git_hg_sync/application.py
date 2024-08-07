from mozlog import get_proxy_logger

from git_hg_sync.mapping import Mapping, MappingMatch
from git_hg_sync.pulse_worker import PulseWorker
from git_hg_sync.repo_synchronizer import RepoSynchronizer
from git_hg_sync.events import Push, Tag

logger = get_proxy_logger(__name__)


class Application:

    def __init__(
        self,
        worker: PulseWorker,
        repo_synchronizers: dict[str, RepoSynchronizer],
        mappings: list[Mapping],
    ):
        self._worker = worker
        self._worker.event_handler = self._handle_event
        self._repo_synchronizers = repo_synchronizers
        self._mappings = mappings

    def run(self) -> None:
        self._worker.run()

    def _handle_push_event(self, push_event: Push) -> None:
        logger.info("Handling push event.")
        synchronizer = self._repo_synchronizers[push_event.repo_url]
        matches_by_destination: dict[str, list[MappingMatch]] = {}

        for mapping in self._mappings:
            if matches := mapping.match(push_event):
                for match in matches:
                    matches_by_destination.setdefault(match.destination_url, []).append(
                        match
                    )

        for destination, matches in matches_by_destination.items():
            refspecs = []
            for match in matches:
                refspecs.append((match.source_commit, match.destination_branch))
            synchronizer.sync_branches(destination, refspecs)

    def _handle_event(self, event: Push | Tag) -> None:
        if event.repo_url not in self._repo_synchronizers:
            logger.info("Ignoring event for untracked repository: %()s", event.repo_url)
            return
        match event:
            case Push():
                self._handle_push_event(event)
            case _:
                raise NotImplementedError()
