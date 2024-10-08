import pytest

from git_hg_sync.events import Push, Tag
from git_hg_sync.pulse_worker import EntityTypeError, PulseWorker


def raw_push_entity():
    return {
        "type": "push",
        "repo_url": "repo_url",
        "branches": {"mybranch": "acommitsha"},
        "time": 0,
        "pushid": 0,
        "user": "user",
        "push_json_url": "push_json_url",
    }


def raw_tag_entity():
    return {
        "type": "tag",
        "repo_url": "repo_url",
        "tag": "tag",
        "commit": "commit",
        "time": 0,
        "pushid": 0,
        "user": "user",
        "push_json_url": "push_json_url",
    }


def test_parse_entity_valid() -> None:
    push_entity = PulseWorker.parse_entity(raw_push_entity())
    assert isinstance(push_entity, Push)
    tag_entity = PulseWorker.parse_entity(raw_tag_entity())
    assert isinstance(tag_entity, Tag)


def test_parse_invalid_type() -> None:
    with pytest.raises(EntityTypeError):
        PulseWorker.parse_entity({"type": "unknown"})
