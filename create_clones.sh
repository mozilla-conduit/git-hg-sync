#!/bin/sh -ex

CLONES_DIR="${1:-clones}"

export HOME=/tmp

REPO=test-repo
HG_REPO_URL="https://hg.mozilla.org/conduit-testing/${REPO}/"
HG_REPO_CLONE="${CLONES_DIR}/${REPO}-hg"
GIT_REPO_CLONE="${CLONES_DIR}/${REPO}-git"

BRANCHES="esr115 esr128"
TAGS="FIREFOX_BETA_136"

test -d "${HG_REPO_CLONE}" && exit

mkdir -p "${CLONES_DIR}"

GIT_SSH="ssh -oStrictHostKeyChecking=accept-new"

hg clone --ssh "$GIT_SSH" "${HG_REPO_URL}" "${HG_REPO_CLONE}"
hg --cwd "${HG_REPO_CLONE}" branch tags
hg --cwd "${HG_REPO_CLONE}" commit -m "Created tags branch"

git clone "hg::${HG_REPO_CLONE}" "${GIT_REPO_CLONE}"

cd "${GIT_REPO_CLONE}" || exit 1

# for git-cinnabar to be happier:
git config fetch.prune true
# make git status and friends faster:
# mv .git/hooks/fsmonitor-watchman.sample .git/hooks/query-watchman
# git config core.fsmonitor .git/hooks/query-watchman
# add git origin
# git remote add git_chatzilla http://github.com/djangoliv/chatzilla.git

# conf
git config remote.origin.skipDefaultUpdate true
git remote set-url --push origin hg::ssh://git@forge.extranet.logilab.fr/ogiorgis/chatzilla
git config remote.origin.push +HEAD:refs/heads/branches/default/tip
# git pull git_chatzilla
# check
git cinnabar fsck

for b in ${BRANCHES}; do
  git branch "${b}"
done

for t in ${TAGS}; do
  git tag "${t}_END"
  git tag "${t}_START" HEAD~10
done

cd -

for b in ${BRANCHES} beta; do
  cp -r "${HG_REPO_CLONE}" "${CLONES_DIR}/mozilla-${b}"
done
