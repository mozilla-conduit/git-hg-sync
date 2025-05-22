import logging
import os

import flask

from git_hg_sync import PID_FILEPATH

app = flask.Flask(__name__)


@app.route("/__lbheartbeat__")
def lb_heartbeat() -> flask.Response:
    return flask.Response("ok")


@app.route("/__heartbeat__")
def heartbeat() -> flask.Response:
    try:
        pid = int(PID_FILEPATH.read_text().strip())
    except (OSError, ValueError):
        return flask.Response("failed to read pidfile", status=503)

    try:
        # Test is a process with this PID is still running.
        # Returns 0 if so, or raises OSError otherwise.
        os.kill(pid, 0)
    except OSError:
        return flask.Response(f"pid {pid} not running", status=503)
    return flask.Response(f"ok: pid {pid} running", status=200)


@app.route("/")
def index() -> flask.Response:
    return flask.Response(
        "<pre>git-hg-sync\n"
        '<a href="__lbheartbeat__">__lbheartbeat__</a>\n'
        '<a href="__heartbeat__">__heartbeat__</a>\n'
        "</pre>"
    )


if __name__ == "__main__":
    logging.getLogger("werkzeug").setLevel(logging.INFO)
    app.run(port=int(os.environ.get("PORT", "8000")), debug=False)
