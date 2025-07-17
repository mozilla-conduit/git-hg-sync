#!/usr/bin/env bash

VER=0.7.3

curl https://raw.githubusercontent.com/glandium/git-cinnabar/${VER}/download.py -o download.py
chmod u+x download.py
./download.py --exact ${VER}
chmod a+x git-cinnabar
chmod a+x git-remote-hg
