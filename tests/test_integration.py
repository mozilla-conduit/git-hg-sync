import os
import subprocess
from pathlib import Path
from typing import Any

import kombu
import pulse_utils
import pytest
from git import Repo
from mozlog import get_proxy_logger
from utils import hg_cat, hg_log, hg_rev

from git_hg_sync.__main__ import get_connection, get_queue, start_app
from git_hg_sync.config import Config, PulseConfig

NO_RABBITMQ = os.getenv("RABBITMQ") != "true"
HERE = Path(__file__).parent


@pytest.mark.skipif(NO_RABBITMQ, reason="This test doesn't work without rabbitMq")
def test_send_and_receive(pulse_config: PulseConfig) -> None:
    payload = {
        "type": "push",
        "repo_url": "repo.git",
        "branches": {},
        "tags": {},
        "time": 0,
        "push_id": 0,
        "user": "user",
        "push_json_url": "push_json_url",
    }

    def callback(body: Any, message: kombu.Message) -> None:
        message.ack()
        assert body["payload"] == payload

    pulse_utils.send_pulse_message(pulse_config, payload, purge=True)
    connection = get_connection(pulse_config)
    queue = get_queue(pulse_config)
    with connection.Consumer(queue, auto_declare=False, callbacks=[callback]):
        connection.drain_events(timeout=5)


@pytest.mark.skipif(NO_RABBITMQ, reason="This test doesn't work without rabbitMq")
def test_full_app(
    tmp_path: Path,
) -> None:
    # Create a remote mercurial repository
    hg_remote_repo_path = tmp_path / "hg-remotes" / "mozilla-esr128"
    hg_remote_repo_path.mkdir(parents=True)
    subprocess.run(["hg", "init"], cwd=hg_remote_repo_path, check=True)

    # Create a remote git repository
    git_remote_repo_path = tmp_path / "git-remotes" / "firefox-releases"
    # Create an initial commit on git
    repo = Repo.init(git_remote_repo_path, b="esr128")
    foo_path = git_remote_repo_path / "foo.txt"
    foo_path.write_text("FOO CONTENT")
    repo.index.add([foo_path])
    repo.index.commit("add foo.txt")

    # Push to mercurial repository
    subprocess.run(
        [
            "git",
            "push",
            "hg::" + str(hg_remote_repo_path),
            "esr128:refs/heads/branches/default/tip",
        ],
        cwd=git_remote_repo_path,
        check=True,
    )

    assert "FOO CONTENT" in hg_cat(hg_remote_repo_path, "foo.txt", "default")

    bar_path = git_remote_repo_path / "bar.txt"
    bar_path.write_text("BAR CONTENT")
    repo.index.add([bar_path])
    git_commit_sha = repo.index.commit("add bar.txt").hexsha

    # modify config file to match the tmp dirs
    config_content = Path(HERE / "data" / "config.toml").read_text()
    config_content = config_content.replace("{directory}", str(tmp_path))
    (tmp_path / "config.toml").write_text(config_content)

    # send message
    config = Config.from_file(tmp_path / "config.toml")
    payload = {
        "type": "push",
        "repo_url": str(git_remote_repo_path),
        "branches": {"esr128": git_commit_sha},
        "tags": {"FIREFOX_128_0esr_RELEASE": git_commit_sha},
        "time": 0,
        "push_id": 0,
        "user": "user",
        "push_json_url": "push_json_url",
    }
    # With the test configuration, tag FIREFOX_128_0esr_RELEASE is mapped onto this
    # branch.
    tags_branch = "tags-esr128"
    pulse_utils.send_pulse_message(config.pulse, payload, purge=True)

    # execute app
    start_app(config, get_proxy_logger("test"), one_shot=True)

    # test
    assert "BAR CONTENT" in hg_cat(hg_remote_repo_path, "bar.txt", "default")
    assert "FIREFOX_128_0esr_RELEASE" in hg_cat(
        hg_remote_repo_path, ".hgtags", tags_branch
    )

    # test tag commit message
    tag_log = hg_log(hg_remote_repo_path, tags_branch, ["-T", "{desc}"])
    assert "No bug - Tagging" in tag_log
    assert "FIREFOX_128_0esr_RELEASE" in tag_log
    assert hg_rev(hg_remote_repo_path, "default") in tag_log
