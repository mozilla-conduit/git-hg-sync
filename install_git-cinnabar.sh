#!/usr/bin/env bash

VER=9d4dea7f4752136bc816cc288a318818589495a0
# Comment this out if not currently relying on a release.
TAG=0.7.5

curl https://raw.githubusercontent.com/glandium/git-cinnabar/${VER}/download.py -o download.py
chmod u+x download.py
./download.py --exact ${TAG:-${VER}}
chmod a+x git-cinnabar
chmod a+x git-remote-hg
