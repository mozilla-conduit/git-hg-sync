# git-hg-sync

A Python service that can sync new changes landing in the Git repository back into the Mercurial repository
automatically.
This synchronisation must allow infrastructure teams to incrementally migrate tasks from
using Mercurial to using Git.

## Principle

This service (sync rather than async) receives messages from RabbitMQ. These messages are lists
of pushed commits (the unit of work being a push, not a commit, not a pull request, not a branch,
etc).

The Python service has locally a clone of the git repository and the mercurial repositories.
After receiving the message, it fetches the news commits to the git repo, then executes git-cinnabar
to produce the equivalent mercurial commits to the right repo (depending on the git branch).

It finally pushes the changes to the remote mercurial repository… then goes back to step one to
process the next message in the queue.

## build and test

```console
$ mkdir -p tests_output
$ chmod a+w tests_output
$ docker-compose build
$ docker-compose run --rm sync
```

## Known limitations

- Merge commits cannot be pushed to mercurial repositories;
- The target mercurial repository must exist in order to be able to push to it;
