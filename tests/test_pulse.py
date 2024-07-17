from git_hg_sync import pulse_sender, sync

payload = {
    "type": "push",
    "repo_url": "repo_url",
    "heads": ["head"],
    "commits": ["commit"],
    "time": 0,
    "pushid": 0,
    "user": "user",
    "push_json_url": "push_json_url",
}


def mocked_callback(body, message):
    assert body["payload"] == payload


def test_pulse():
    pulse_sender.send_pulse_message(payload)
    sync.callback = mocked_callback
    sync.main(True)
