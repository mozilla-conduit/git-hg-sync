from pathlib import Path

import pytest
from pydantic import ValidationError

from git_hg_sync.config import Config

BASEDIR = Path(__file__).parent.parent


@pytest.mark.parametrize("config_file", list(BASEDIR.glob("config-*.toml")))
def test_config_files(config_file: Path) -> None:
    try:
        config = Config.from_file(config_file)
    except ValidationError as exc:
        raise AssertionError(f"Syntax in {config_file}") from exc

    # We just do a shallow verification. What we really care is that the file could be
    # loaded correctly.
    assert config.pulse, f"`pulse` section missing in {config_file}"
    assert config.tracked_repositories, (
        f"`tracked_repositories` section missing in {config_file}"
    )
    assert config.branch_mappings, f"`branch_mappings` section missing in {config_file}"
    assert config.tag_mappings, f"`tag_mappings` section missing in {config_file}"
