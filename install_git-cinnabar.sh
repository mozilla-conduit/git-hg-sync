#!/usr/bin/env bash

VER=f434ffd01405f62151f702fcf0593fe4c0dd45ea
# Comment this out if not currently relying on a release.
TAG=0.7.4

curl https://raw.githubusercontent.com/glandium/git-cinnabar/${VER}/download.py -o download.py
chmod u+x download.py
./download.py --exact ${TAG:-${VER}}
chmod a+x git-cinnabar
chmod a+x git-remote-hg
