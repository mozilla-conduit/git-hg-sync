#!/usr/bin/env bash

curl https://raw.githubusercontent.com/glandium/git-cinnabar/master/download.py -o download.py
chmod u+x download.py
./download.py --exact 19ead4b40b57c96a02d8cc3927dd08bd7c55d1d9
chmod a+x git-cinnabar
chmod a+x git-remote-hg
