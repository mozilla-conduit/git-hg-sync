from git_hg_sync.pulse_worker import PulseWorker
from git_hg_sync.repo_synchronizer import RepoSynchronizer
from git_hg_sync.events import Push, Tag


class Application:

    def __init__(self, worker: PulseWorker, repo_synchronizer: RepoSynchronizer):
        self._worker = worker
        self._worker.event_handler = self._handle_event
        self._repo_synchronizer = repo_synchronizer

    def run(self) -> None:
        self._worker.run()

    def _handle_event(self, event: Push | Tag):
        self._repo_synchronizer.sync(event)
