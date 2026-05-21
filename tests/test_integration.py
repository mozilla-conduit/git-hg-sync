import os
import subprocess
from collections.abc import Callable
from configparser import ConfigParser
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
from git_hg_sync.events import Event
from git_hg_sync.pulse_worker import PulseWorker

NO_RABBITMQ = os.getenv("RABBITMQ") != "true"
HERE = Path(__file__).parent


@pytest.mark.parametrize(
    "queue_key",
    (
        (""),  # Use the default from the config.
        ("one"),
        ("two.three"),
    ),
)
@pytest.mark.skipif(NO_RABBITMQ, reason="This test doesn't work without RabbitMQ")
def test_send_and_receive(
    request: pytest.FixtureRequest,
    pulse_config: PulseConfig,
    get_payload: Callable,
    queue_key: str,
) -> None:
    payload = get_payload(request=request)

    if queue_key:
        pulse_config.routing_key = queue_key
        pulse_config.queue = f"{pulse_config.queue}-{queue_key}"

    def callback(body: Any, message: kombu.Message) -> None:
        message.ack()
        assert body["payload"] == payload

    # Create queue and bindings prior to sending.
    _, _ = _setup_connection_and_queue(pulse_config)

    connection, queue = pulse_utils.send_pulse_message(
        pulse_config, payload, purge=True
    )

    with connection.Consumer(queue, auto_declare=False, callbacks=[callback]):
        connection.drain_events(timeout=5)


@pytest.mark.skipif(NO_RABBITMQ, reason="This test doesn't work without RabbitMQ")
@pytest.mark.parametrize(
    "send_key,queue_key",
    (
        ("three", "three.four"),
        ("five.six", "five"),
    ),
)
def test_send_and_receive_routing_key_mismatch(
    pulse_config: PulseConfig, get_payload: Callable, send_key: str, queue_key: str
) -> None:
    payload = get_payload()

    def callback(_body: Any, _message: kombu.Message) -> None:
        raise AssertionError("No message should be received")

    pulse_config.routing_key = queue_key
    # We need to create a unique queue for this binding.
    pulse_config.queue = f"{pulse_config.queue}-{send_key}-{queue_key}"

    pulse_config_sender = pulse_config.model_copy()
    pulse_config_sender.routing_key = send_key

    connection, queue = _setup_connection_and_queue(pulse_config)
    pulse_utils.send_pulse_message(pulse_config_sender, payload, purge=True)

    with (
        connection.Consumer(queue, auto_declare=False, callbacks=[callback]),
        pytest.raises(TimeoutError),
    ):
        connection.drain_events(timeout=5)


@pytest.mark.skipif(NO_RABBITMQ, reason="This test doesn't work without RabbitMQ")
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
    git_repo_name = "firefox-releases"
    git_remote_repo_path = tmp_path / "git-remotes" / git_repo_name
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

    # test that the working repository is a bare repo
    git_clone_config_path = config.clones.directory / git_repo_name / "config"
    assert not (git_clone_config_path / ".git").exists(), (
        "Found .git in {git_clone_config_path}, it should be a bare repo"
    )
    assert git_clone_config_path.exists(), (
        "Cannot find git clone config at {git_clone_config_path}, is it a bare repo?"
    )
    git_clone_config = ConfigParser()
    with git_clone_config_path.open("r") as fp:
        git_clone_config.read_file(fp)
    assert git_clone_config["core"]["bare"], "Working copy clone is not a bare repo"
    assert (
        git_clone_config["cinnabar"]["experiments"] == "branch,tag,git_commit,merge"
    ), "Incorrect git cinnabar.experiments configuration set"

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


@pytest.mark.skipif(NO_RABBITMQ, reason="This test doesn't work without RabbitMQ")
def test_no_duplicated_ack_messages(
    test_config: Config,
    get_payload: Callable,
) -> None:
    """This test checks that long-running messages are not processed more than once.

    It may also timeout, which is likely indicative of the same issue.
    """
    payload = get_payload()

    wait = 30

    connection, queue = _setup_connection_and_queue(test_config.pulse)

    worker = PulseWorker(connection, queue, one_shot=True)

    callback = mock.MagicMock()
    callback.side_effect = lambda _event: sleep(wait)
    worker.event_handler = callback

    pulse_utils.send_pulse_message(test_config.pulse, payload, purge=True)
    worker.run()

    callback.assert_called_once()


@pytest.mark.skipif(NO_RABBITMQ, reason="This test doesn't work without RabbitMQ")
def test_messages_in_order(
    test_config: Config,
    get_payload: Callable,
) -> None:
    """This test checks that long-running messages are not processed more than once.

    It may also timeout, which is likely indicative of the same issue.
    """
    connection, queue = _setup_connection_and_queue(test_config.pulse)

    worker = PulseWorker(connection, queue, one_shot=False)

    events_log = []

    def event_handler(event: Event) -> None:
        push_id = event.push_id
        already_seen = push_id in events_log

        events_log.append(push_id)

        # Terminate the worker after processing the expected number of messages.
        if len(events_log) == 4:
            worker.should_stop = True

        if not already_seen:
            raise Exception("Not seen yet")

    worker.event_handler = event_handler

    pulse_utils.send_pulse_message(
        test_config.pulse, get_payload(push_id=0), purge=True
    )
    pulse_utils.send_pulse_message(
        test_config.pulse, get_payload(push_id=1), purge=False
    )
    worker.run()

    assert events_log == [0, 0, 1, 1]


def _setup_connection_and_queue(
    pulse_config: PulseConfig,
) -> tuple[kombu.Connection, kombu.Queue]:
    connection = get_connection(pulse_config)
    queue = get_queue(pulse_config)
    queue(connection).queue_declare()
    queue(connection).queue_bind()
    return connection, queue
