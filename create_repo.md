# Repo creation

```console
$ cd clones
$ git clone hg::ssh://git@forge.extranet.logilab.fr/ogiorgis/chatzilla chatzilla_cinnabar
$ cd chatzilla_cinnabar
$ # for git-cinnabar to be happier:
$ git config fetch.prune true
$ # make git status and friends faster:
$ mv .git/hooks/fsmonitor-watchman.sample .git/hooks/query-watchman
$ git config core.fsmonitor .git/hooks/query-watchman
$ # add git origin
$ git remote add git_chatzilla http://github.com/djangoliv/chatzilla.git
$ # conf
$ git config remote.origin.skipDefaultUpdate true
$ git remote set-url --push origin hg::ssh://git@forge.extranet.logilab.fr/ogiorgis/chatzilla
$ git config remote.origin.push +HEAD:refs/heads/branches/default/tip
$ git pull git_chatzilla
$ # check
$ git cinnabar fsck
```
