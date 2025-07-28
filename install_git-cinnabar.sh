#!/usr/bin/env bash

VER=3f0a8a4c35b5be88ddc229c0dd099b99c67483ce

curl https://raw.githubusercontent.com/glandium/git-cinnabar/${VER}/download.py -o download.py
chmod u+x download.py
./download.py --exact ${VER}
chmod a+x git-cinnabar
chmod a+x git-remote-hg
