import signal
import time
from pathlib import Path
from subprocess import PIPE, Popen

import pytest
from pydantic import ValidationError

from git_hg_sync.events import Push
from git_hg_sync.pulse_worker import EntityTypeError, PulseWorker

HERE = Path(__file__).parent


@pytest.fixture
def raw_push_entity() -> dict:
    return {
        "type": "push",
        "repo_url": "repo_url",
        "branches": {"mybranch": "acommitsha"},
        "tags": {"mytag": "acommitsha"},
        "time": 0,
        "pushid": 0,
        "user": "user",
        "push_json_url": "push_json_url",
    }


def test_parse_entity_valid(raw_push_entity: dict) -> None:
    push_entity = PulseWorker.parse_entity(raw_push_entity)
    assert isinstance(push_entity, Push)


def test_parse_invalid_type(raw_push_entity: dict) -> None:
    with pytest.raises(EntityTypeError):
        raw_push_entity["type"] = "unknown"
        PulseWorker.parse_entity(raw_push_entity)


def test_parse_invalid_data_types(raw_push_entity: dict) -> None:
    with pytest.raises(ValidationError):
        raw_push_entity["branches"] = ["main"]
        PulseWorker.parse_entity(raw_push_entity)


def test_sigint_signal_interception() -> None:
    config_file = HERE / "data" / "config.toml"
    module_path = HERE.parent / "git_hg_sync" / "__main__.py"
    process = Popen(
        ["python", module_path, "-c", config_file], shell=True, stdout=PIPE, stderr=PIPE
    )
    time.sleep(1)
    process.send_signal(signal.SIGINT)
    time.sleep(1)
    try:
        assert process.returncode == 0
    except AssertionError as e:
        process.kill()
        raise e
