from typing import TYPE_CHECKING
from unittest import mock

import pytest

from git_hg_sync import cli

if TYPE_CHECKING:
    from git_hg_sync.config import Config


@pytest.mark.parametrize(
    "command", [[], ["config"], ["dequeue"], ["fetchrepo"], ["pause"], ["resume"]]
)
def test_cli_help(monkeypatch: pytest.MonkeyPatch, command: list[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        _run_cli(monkeypatch, [*command, "--help"])
    assert exc_info.value.code == 0


@mock.patch("git_hg_sync.cli.Config.from_file")
@mock.patch("git_hg_sync.cli.RepoSynchronizer.get_clone_repo")
@mock.patch("git_hg_sync.cli.RepoSynchronizer.fetch_all_from_remote")
def test_cli_fetchrepo(
    mock_fetch_all_from_remote: mock.Mock,
    mock_get_clone_repo: mock.Mock,
    mock_config_from_file: mock.Mock,
    test_config: Config,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    test_config.branch_mappings[0].intermediate_fetch = ["aaa"]
    mock_config_from_file.return_value = test_config

    repo = mock.MagicMock()
    mock_get_clone_repo.return_value = repo

    _run_cli(
        monkeypatch,
        [
            "fetchrepo",
            "--repository-url",
            test_config.tracked_repositories[0].url,
            "--fetch-all",
        ],
    )

    assert mock_get_clone_repo.call_count == 1, "Should have clone the source repo"
    assert mock_fetch_all_from_remote.call_count == 2, (
        "Should have fetched from all remotes"
    )
    mock_fetch_all_from_remote.assert_any_call(
        repo,
        f"hg::{test_config.branch_mappings[0].destination_url}",
        intermediate_fetch=test_config.branch_mappings[0].intermediate_fetch,
        verbose=False,
    )


def _run_cli(monkeypatch: pytest.MonkeyPatch, args: list[str]) -> None:
    monkeypatch.setattr("sys.argv", ["git-hg-cli", *args])
    cli.main()
