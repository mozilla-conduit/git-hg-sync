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
  exec /usr/local/bin/git-hg-sync "${@}"
  ;;
esac
