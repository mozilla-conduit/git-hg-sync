from pathlib import Path

from git_hg_sync.config import Config

HERE = Path(__file__).parent


def test_load_config() -> None:
    config = Config.from_file(HERE / "data" / "config.toml")
    assert not config.pulse.ssl
    assert config.branch_mappings[0].destination_branch == "default"
