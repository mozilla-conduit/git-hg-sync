#!/usr/bin/env bash

curl https://raw.githubusercontent.com/glandium/git-cinnabar/master/download.py -o download.py
chmod u+x download.py
./download.py --exact 4beaf11666a48d5fac1660d6ceca09d1ffa406c6
chmod a+x git-cinnabar
chmod a+x git-remote-hg
