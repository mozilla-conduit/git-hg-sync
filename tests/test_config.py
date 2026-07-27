from pathlib import Path

import pytest
import tomllib

from git_hg_sync.config import Config, PulseConfig
from git_hg_sync.events import Push

HERE = Path(__file__).parent


def test_load_config() -> None:
    config = Config.from_file(HERE / "data" / "config.toml")
    assert not config.pulse.ssl
    assert config.pulse.host == "pulse"
    assert config.branch_mappings[0].destination_branch == "default"


def test_load_config_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    overrides = {
        "pulse": {
            "exchange": "overridden exchange",
            "host": "overridden host",
            "password": "overridden password",
            "port": "1337",
            "queue": "overridden queue",
            "routing_key": "overridden routing_key",
            "ssl": "True",
            "userid": "overridden userid",
            "heartbeat": "42",
        },
        "sentry": {
            "sentry_dsn": "overridden sentry_dsn",
        },
    }

    no_prefix_sections = ["sentry"]

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
            # The original override value is an int, so we cast the config value back,
            # for equality check.
            assert str(getattr(section_config, var)) == value, (
                f"Configuration not overridden for {section}.{var}"
            )


def test_unique_tracked_repository_name() -> None:
    config = tomllib.loads((HERE / "data" / "config.toml").read_text())

    # Ensure this doesn't fail without duplicates.
    _ = Config(**config)

    config["tracked_repositories"].append(config["tracked_repositories"][0])

    with pytest.raises(ValueError, match="non-unique names"):
        _ = Config(**config)


@pytest.mark.parametrize(
    "source_url,source_branch,expected_urls,expected_branches",
    [
        ("not-a-match", "doesn't matter", [], []),
        ("{directory}/git-remotes/firefox-releases", "not-a-match", [], []),
        (
            "{directory}/git-remotes/firefox-releases",
            "test12",
            ["{directory}/hg-remotes/mozilla-test12"],
            ["mozilla-test12"],
        ),
    ],
)
def test_branch_mapping(
    source_url: str,
    source_branch: str,
    expected_urls: list[str],
    expected_branches: list[str],
) -> None:
    config = Config.from_file(HERE / "data" / "config.toml")

    event = Push(
        repo_url=source_url,
        branches={source_branch: "commitsha"},
        # What's below is not important for the test.
        push_id=1,
        push_json_url="push_json_url",
        time=0,
        user="user",
    )

    operations = {}

    for mapping in config.branch_mappings:
        if matches := mapping.match(event):
            for match in matches:
                operations.setdefault(match.destination_url, []).append(match.operation)

    destination_urls = list(operations)
    destination_branches = [
        sync_branch_operation.destination_branch
        for url in operations
        for sync_branch_operation in operations[url]
    ]

    assert destination_urls == expected_urls
    assert destination_branches == expected_branches

    # tags_mappings = config.tag_mappings


@pytest.mark.parametrize(
    "source_url,tag,expected_urls,expected_branches",
    [
        ("not-a-match", "doesn't matter", [], []),
        ("{directory}/git-remotes/firefox-releases", "not-a-match", [], []),
        (
            "{directory}/git-remotes/firefox-releases",
            "FIREFOX_12_1_0esr_BUILD1",
            ["{directory}/hg-remotes/mozilla-esr12"],
            ["tags-esr12"],
        ),
    ],
)
def test_tag_mapping(
    source_url: str,
    tag: str,
    expected_urls: list[str],
    expected_branches: list[str],
) -> None:
    config = Config.from_file(HERE / "data" / "config.toml")

    event = Push(
        repo_url=source_url,
        tags={tag: "commitsha"},
        # What's below is not important for the test.
        push_id=1,
        push_json_url="push_json_url",
        time=0,
        user="user",
    )

    operations = {}

    for mapping in config.tag_mappings:
        if matches := mapping.match(event):
            for match in matches:
                operations.setdefault(match.destination_url, []).append(match.operation)

    destination_urls = list(operations)
    destination_tags = [
        sync_tag_operation.tags_destination_branch
        for url in operations
        for sync_tag_operation in operations[url]
    ]

    assert destination_urls == expected_urls
    assert destination_tags == expected_branches

    # tags_mappings = config.tag_mappings


@pytest.mark.parametrize(
    "field_name",
    (
        "host",
        "exchange",
        "userid",
        "password",
        "routing_key",
        "queue",
    ),
)
def test_pulse_not_empty(field_name: str) -> None:
    test_config_file = HERE / "data" / "config.toml"
    with test_config_file.open("rb") as config_file:
        config = tomllib.load(config_file)
    pulse_config = config["pulse"]
    pulse_config[field_name] = ""

    with pytest.raises(ValueError, match=f"{field_name} cannot be empty"):
        PulseConfig(**pulse_config)
