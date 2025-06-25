#!/usr/bin/env bash

curl https://raw.githubusercontent.com/glandium/git-cinnabar/master/download.py -o download.py
chmod u+x download.py
./download.py --exact 8a2959e3d04781179f80ba47288ee8af800112bb
chmod a+x git-cinnabar
chmod a+x git-remote-hg
