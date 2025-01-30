from pathlib import Path

PID_FILEPATH = (
    Path("/app/pidfile")
    if Path("/app").is_dir()
    else Path(__file__).resolve().parent.parent / "pidfile"
)
