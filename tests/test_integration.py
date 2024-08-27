import os
import subprocess
from pathlib import Path

import pulse_utils
import pytest
from git import Repo
from mozlog import get_proxy_logger

from git_hg_sync.__main__ import get_connection, get_queue, start_app
from git_hg_sync.config import Config

NO_RABBITMQ = not (os.getenv("RABBITMQ") == "true")
HERE = Path(__file__).parent


@pytest.mark.skipif(NO_RABBITMQ, reason="This test doesn't work without rabbitMq")
def test_send_and_receive(pulse_config):

    payload = {
        "type": "tag",
        "repo_url": "repo.git",
        "tag": "Tag",
        "commit": "sha",
        "time": 0,
        "pushid": 0,
        "user": "user",
        "push_json_url": "push_json_url",
    }

    def callback(body, message):
        message.ack()
        assert body["payload"] == payload

    pulse_utils.send_pulse_message(pulse_config, payload, purge=True)
    connection = get_connection(pulse_config)
    queue = get_queue(pulse_config)
    with connection.Consumer(queue, auto_declare=False, callbacks=[callback]):
        connection.drain_events(timeout=2)


@pytest.mark.skipif(NO_RABBITMQ, reason="This test doesn't work without rabbitMq")
def test_full_app(
    tmp_path: Path,
) -> None:
    # Create a remote git repository
    git_remote_repo_path = tmp_path / "git-remotes" / "firefox-releases"
    repo = Repo.init(git_remote_repo_path)
    foo_path = git_remote_repo_path / "foo.txt"
    foo_path.write_text("FOO CONTENT")
    repo.index.add([foo_path])
    git_commit_sha = repo.index.commit("add foo.txt").hexsha

    # Create a remote mercurial repository
    hg_remote_repo_path = tmp_path / "hg-remotes" / "mozilla-esr12"
    hg_remote_repo_path.mkdir(parents=True)
    subprocess.run(["hg", "init"], cwd=hg_remote_repo_path, check=True)

    # modify config file to match the tmp dirs
    config_content = Path(HERE / "data" / "config.toml").read_text()
    config_content = config_content.replace("{directory}", str(tmp_path))
    (tmp_path / "config.toml").write_text(config_content)

    # send message
    config = Config.from_file(tmp_path / "config.toml")
    payload = {
        "type": "push",
        "repo_url": str(git_remote_repo_path),
        "branches": {"esr12": git_commit_sha},
        "time": 0,
        "pushid": 0,
        "user": "user",
        "push_json_url": "push_json_url",
    }
    pulse_utils.send_pulse_message(config.pulse, payload, purge=True)

    # execute app
    start_app(config, get_proxy_logger("test"), one_shot=True)

    # tests
    process = subprocess.run(
        ["hg", "export", "tip"],
        cwd=hg_remote_repo_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "FOO CONTENT" in process.stdout
