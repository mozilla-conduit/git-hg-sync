import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from time import sleep
from typing import Any
from unittest import mock

import kombu
import pulse_utils
import pytest
from git import Repo
from mozlog import get_proxy_logger
from utils import hg_cat, hg_log, hg_rev

from git_hg_sync.__main__ import get_connection, get_queue, start_app
from git_hg_sync.config import Config, PulseConfig
from git_hg_sync.pulse_worker import PulseWorker

NO_RABBITMQ = os.getenv("RABBITMQ") != "true"
HERE = Path(__file__).parent


@pytest.mark.skipif(NO_RABBITMQ, reason="This test doesn't work without rabbitMq")
def test_send_and_receive(pulse_config: PulseConfig, get_payload: Callable) -> None:
    payload = get_payload()

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
    get_payload: Callable,
) -> None:
    # With the test configuration, our local branch and tags should map to those
    # destinations.
    local_branch = "esr128"
    local_tag = "FIREFOX_128_0esr_RELEASE"
    destination_branch = "default"
    destination_tags_branch = "tags-esr128"

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

    # Push the base to mercurial repository
    subprocess.run(
        [
            "git",
            "push",
            "hg::" + str(hg_remote_repo_path),
            f"{local_branch}:refs/heads/branches/{destination_branch}/tip",
        ],
        cwd=git_remote_repo_path,
        check=True,
    )

    assert "FOO CONTENT" in hg_cat(hg_remote_repo_path, "foo.txt", destination_branch)

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
    payload = get_payload(
        repo_url=str(git_remote_repo_path),
        branches={local_branch: git_commit_sha},
        tags={local_tag: git_commit_sha},
    )
    pulse_utils.send_pulse_message(config.pulse, payload, purge=True)

    # execute app
    start_app(config, get_proxy_logger("test"), one_shot=True)

    # test
    assert "BAR CONTENT" in hg_cat(hg_remote_repo_path, "bar.txt", destination_branch)
    assert "FIREFOX_128_0esr_RELEASE" in hg_cat(
        hg_remote_repo_path, ".hgtags", destination_tags_branch
    )

    # test tag commit message
    tag_log = hg_log(hg_remote_repo_path, destination_tags_branch, ["-T", "{desc}"])
    assert "No bug - Tagging" in tag_log
    assert "FIREFOX_128_0esr_RELEASE" in tag_log
    assert hg_rev(hg_remote_repo_path, destination_branch) in tag_log


@pytest.mark.skipif(NO_RABBITMQ, reason="This test doesn't work without rabbitMq")
def test_no_duplicated_ack_messages(
    test_config: Config,
    get_payload: Callable,
) -> None:
    """This tests checkes that a long-running message is not processed more than
    once.

    It may also timeout, which is likely indicative of the same issue.
    """
    payload = get_payload()

    wait = 30

    connection = get_connection(test_config.pulse)
    queue = get_queue(test_config.pulse)
    queue(connection).queue_declare()
    queue(connection).queue_bind()

    worker = PulseWorker(connection, queue, one_shot=True)

    callback = mock.MagicMock()
    callback.side_effect = lambda _event: sleep(wait)
    worker.event_handler = callback

    pulse_utils.send_pulse_message(test_config.pulse, payload, purge=True)
    worker.run()

    callback.assert_called_once()
