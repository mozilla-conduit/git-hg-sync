#!/bin/sh
set -e

# start web server (for dockerflow)
PORT="${PORT:-8000}"
export PYTHONUNBUFFERED=1
gunicorn \
  --bind 0.0.0.0:$PORT \
  --workers 2 \
  --worker-tmp-dir /dev/shm \
  --log-level debug \
  --capture-output \
  --enable-stdio-inheritance \
  --daemon \
  dockerflow:app

# start service
python3 -m git_hg_sync --config config.toml
