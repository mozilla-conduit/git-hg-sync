import pytest

from git_hg_sync import cli


@pytest.mark.parametrize(
    "command", [[], ["config"], ["dequeue"], ["fetchrepo"], ["pause"], ["resume"]]
)
def test_cli_help(monkeypatch: pytest.MonkeyPatch, command: list[str]) -> None:
    monkeypatch.setattr("sys.argv", ["git-hg-cli", *command, "--help"])
    with pytest.raises(SystemExit) as exc_info:
        cli.main()
    assert exc_info.value.code == 0
