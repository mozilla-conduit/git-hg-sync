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
    pulse_env = {
        "exchange": "overridden exchange",
        "host": "overridden host",
        "password": "overridden password",
        "port": "overridden port",
        "queue": "overridden queue",
        "routing_key": "overridden routing_key",
        "ssl": "false",
        "userid": "overridden userid",
    }

    for key in pulse_env:  # noqa: PLC0206 We want the key only here...
        monkeypatch.setenv(f"PULSE_{key}".upper(), pulse_env[key])

    config = Config.from_file(HERE / "data" / "config.toml")

    for key in pulse_env:  # noqa: PLC0206
        assert getattr(config.pulse, key) == pulse_env[key], (
            f"Pulse configuration not overridden for {key}"
        )
