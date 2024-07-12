import os
from git_hg_sync import pulse_sender, pulse_consumer


def test_pulse():
    userid = "ogiorgis"
    exchange = "exchange/ogiorgis/test"
    host = "pulse.mozilla.org"
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
    password = os.environ["PULSE_PASSWORD"]
    pulse_sender.send_pulse_message(userid, password, exchange, host, payload)
    pulse_consumer.drain()
