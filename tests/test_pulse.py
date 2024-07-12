from git_hg_sync import pulse_sender, pulse_consumer


def test_pulse():
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
    pulse_sender.send_pulse_message(payload)
    pulse_consumer.drain()
