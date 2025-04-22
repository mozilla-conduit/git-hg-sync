from pathlib import Path

from pytest import MonkeyPatch

from git_hg_sync.config import Config

HERE = Path(__file__).parent


def test_load_config() -> None:
    config = Config.from_file(HERE / "data" / "config.toml")
    assert not config.pulse.ssl
    assert config.pulse.host == "pulse"
    assert config.branch_mappings[0].destination_branch == "default"


def test_load_config_env_override(monkeypatch: MonkeyPatch) -> None:
    overrides = {
        "pulse": {
            "exchange": "overridden exchange",
            "host": "overridden host",
            "password": "overridden password",
            "port": "overridden port",
            "queue": "overridden queue",
            "routing_key": "overridden routing_key",
            "ssl": "false",
            "userid": "overridden userid",
        },
    }

    no_prefix_sections = []

    for section, env in overrides.items():
        for var, value in env.items():
            if section in no_prefix_sections:
                monkeypatch.setenv(f"{var}".upper(), value)
            else:
                monkeypatch.setenv(f"{section}_{var}".upper(), value)

    config = Config.from_file(HERE / "data" / "config.toml")

    for section, env in overrides.items():
        for var, value in env.items():
            section_config = getattr(config, section)
            assert getattr(section_config, var) == value, (
                f"Configuration not overridden for {section}.{var}"
            )
