from pathlib import Path

import pytest
from pydantic import ValidationError

from git_hg_sync.config import Config

BASEDIR = Path(__file__).parent.parent


@pytest.mark.parametrize("config_file", list(BASEDIR.glob("config-*.toml")))
def test_config_files(monkeypatch: pytest.MonkeyPatch, config_file: Path) -> None:
    _prepare_test_for_config(monkeypatch, config_file)

    try:
        config = Config.from_file(config_file)
    except ValidationError as exc:
        raise AssertionError(f"Syntax error in {config_file}: {exc}") from exc

    # We just do a shallow verification. What we really care is that the file could be
    # loaded correctly.
    assert config.pulse, f"`pulse` section missing in {config_file}"
    assert config.tracked_repositories, (
        f"`tracked_repositories` section missing in {config_file}"
    )
    assert config.branch_mappings, f"`branch_mappings` section missing in {config_file}"
    assert config.tag_mappings, f"`tag_mappings` section missing in {config_file}"


@pytest.mark.parametrize("config_file", list(BASEDIR.glob("config-*.toml")))
def test_config_files_intermediate_fetch(
    monkeypatch: pytest.MonkeyPatch, config_file: Path
) -> None:
    """Ensure that intermediate_fetches are the same in all Mappings for a given source_url."""
    _prepare_test_for_config(monkeypatch, config_file)

    config = Config.from_file(config_file)

    intermediate_fetches = {}

    for mapping in config.branch_mappings + config.tag_mappings:
        if mapping.source_url not in intermediate_fetches:
            intermediate_fetches[mapping.source_url] = mapping.intermediate_fetch
            continue

        assert mapping.intermediate_fetch == intermediate_fetches[mapping.source_url], (
            f"Inconsistent intermediate_fetch for {mapping.source_url} in {config_file}: {mapping}"
        )


def _prepare_test_for_config(
    monkeypatch: pytest.MonkeyPatch, config_file: Path
) -> None:
    if "config-suite.toml" in str(config_file):
        pytest.skip("ignoring placeholder file created by suite")

    if "config-production.toml" in str(config_file):
        # The production configuration file deliberately doesn't specify user credentials
        # or queue parameters, as they should be coming from the environment.
        monkeypatch.setenv("PULSE_USERID", "test_userid")
        monkeypatch.setenv("PULSE_PASSWORD", "test_password")
        monkeypatch.setenv("PULSE_ROUTING_KEY", "test_routing_key")
        monkeypatch.setenv("PULSE_QUEUE", "test_queue")
