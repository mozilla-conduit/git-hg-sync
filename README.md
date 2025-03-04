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

## Run

```console
$ docker compose up -d
```

The logs from the syncer can be displayed with

```console
$ docker compose logs -f sync
```

Repositories can be seen on the host in the `clones` subdirectory. Remember to delete if you want to start fresh.

```
$ ls clones
mozilla-beta  mozilla-esr115  mozilla-esr128  test-repo-git  test-repo-hg
```

See the `create_clones.sh` for the creation logic. `test-repo-hg` is the original HG repository (but is otherwise unused), `test-repo-git` is the source Git repository, while the various `mozilla-*` are the targets HG repositories to sync to. The syncer will also create its own `firefox-releases` Git repo to work in.

### AMQP Exchange

The AMQP exchange is available at localhost:5672. The RabbitMQ management interface is available at http://localhost:15672/, and the login and password are `guest` (don't do this at home, or in prod).

The `send` container can be used by piping messages to send via the exchange, into `docker compose run --rm -T  send`. The message can also be received with `docker compose run --rm recv`, if the syncer is not running.

### Example synchronisation

To create, then synchronise a new commit to the `beta` and `esr115` branches, do the following.

```console
$ docker compose exec sync git --git-dir /clones/test-repo-git/.git commit --allow-empty -m 'test commit'
$ REV=$(docker compose exec sync git --git-dir /clones/test-repo-git/.git show -q --pretty=format:%H)
$ TAG=FIREFOX_BETA_42_END
$ docker compose exec sync git --git-dir /clones/test-repo-git/.git tag $TAG $REV
$ echo '{"payload": {"type": "push", "repo_url": "/clones/test-repo-git", "branches": { "beta": "'$REV'", "esr115": "'$REV'" }, "tags": { "'$TAG'": "'$REV'" }, "time": "'`date +%s`'", "user": "'$USER'", "push_json_url": "blu", "pushid": 2 }}' \
  | docker compose run --rm -T  send
```

After successful processing, the new `test commit` should be visible in, e.g.,
the `mozilla-esr115` repo.

```
$ hg --cwd clones/mozilla-esr115 log | head -n 6
changeset:   219:3acba9603e31
tag:         tip
parent:      217:19243c838e62
user:        root <docker@sync>
date:        Tue Mar 18 04:18:41 2025 +0000
summary:     test commit
$ cd ../mozilla-beta
$ hg --cwd clones/mozilla-beta tags | head
tip                              220:d74d8b53e762
FIREFOX_BETA_42_END              219:3acba9603e31
```

A tag can then be created, and synced. For example, `FIREFOX_BETA_42_END` for the `mozilla-beta` repo. Note that the revision that the tags points to needs to exist on the target Mercurial repo prior to creating it. It can be created as part of the same Pulse message, with the `branches` object.

Note: The tags on the Mercurial side should be created on a dedicated branch. As each tag update requires a new commit to be created, however, this would leave commits on the target Hg branch which do not have equivalents on the Git side. Creating them on a separate branch avoids this confusion. Mercurial will detect them all the same.

Note that, in both examples above, both `branches` and `tags` are present, but one is empty. They are both required, but cannot be set at the same time.

## Configuration

An example configuration file can be found in `config.toml.example`. A different
configuration file can be specified with the `--config` (`-c`) option.

In addition, Pulse parameters can be overridden via the following environment
variables:

- PULSE_EXCHANGE
- PULSE_HOST
- PULSE_PASSWORD
- PULSE_PORT (needs to be an integer)
- PULSE_QUEUE
- PULSE_ROUTING_KEY
- PULSE_SSL (needs to be an empty string to be False, otherwise True)
- PULSE_USERID

## Build and test

Format and test/lint code:

```console
$ tox -e format,lint
```

Run tests:

```console
$ docker compose run --rm test
$ docker compose down
```

## Known limitations

- Merge commits cannot be pushed to mercurial repositories;
- The target mercurial repository must exist in order to be able to push to it;
