from pathlib import Path

from git_hg_sync.config import Config

HERE = Path(__file__).parent


def test_load_config():
    config = Config.from_file(HERE / "data" / "config.toml")
    assert not config.pulse.ssl
    assert config.mappings[0].destination.branch == "default"
