#!/bin/bash

if [ -n "${SSH_PRIVATE_KEY:-}" ]; then
  echo "Importing SSH key supplied in \$SSH_PRIVATE_KEY ..."
  eval "$(ssh-agent -s)"
  ssh-add - <<< "${SSH_PRIVATE_KEY}"
  SSH_PRIVATE_KEY='imported'
  export GIT_SSH_COMMAND="ssh -oStrictHostKeyChecking=accept-new"
fi

case "${1:-}" in
  "bash"|"sh")
    exec ${1}
    ;;
  "exec")
    exec ${2:-bash}
    ;;
  *)
    # start web server (for dockerflow)
    PORT="${PORT:-8000}"
    export PYTHONUNBUFFERED=1
    gunicorn \
      --bind "0.0.0.0:$PORT" \
      --workers 2 \
      --worker-tmp-dir /dev/shm \
      --log-level warning \
      --capture-output \
      --enable-stdio-inheritance \
      --daemon \
      dockerflow:app

    # Hack to replace {{ENVIRONMENT}} in the exec-style CMD with the ${ENVIRONMENT} env variable.
    ARGS=("${@}")
    set -- /usr/local/bin/git-hg-sync
    for ARG in "${ARGS[@]}"; do
      set -- "${@}" "$(echo "${ARG}" | sed "s/{{ENVIRONMENT}}/${ENVIRONMENT}/")"
    done

    echo "Running: ${@}"

    exec "${@}"
  ;;
esac
