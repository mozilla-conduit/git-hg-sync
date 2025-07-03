from pathlib import Path

import pytest

from git_hg_sync.config import Config

HERE = Path(__file__).parent


@pytest.mark.parametrize(
    "config_file",
    [
        "config-development.toml",
        "config-docker.toml",
        "config-production.toml",
        "config-staging.toml",
    ],
)
def test_config_files(config_file: str) -> None:
    config = Config.from_file(HERE / ".." / config_file)

    # We just do a shallow verification. What we really care is that the file could be
    # loaded correctly.
    assert config.pulse
    assert config.tracked_repositories
    assert config.branch_mappings
    assert config.tag_mappings
