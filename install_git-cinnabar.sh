#!/usr/bin/env bash

VER=71ac248b7dd7b56ac2cfe764c914a6a3025ea5af

curl https://raw.githubusercontent.com/glandium/git-cinnabar/${VER}/download.py -o download.py
chmod u+x download.py
./download.py --exact ${VER}
chmod a+x git-cinnabar
chmod a+x git-remote-hg
