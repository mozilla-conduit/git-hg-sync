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

See the `create_clones.sh` for the creation logic. `test-repo-hg` is the original Mercurial repository (but is otherwise unused), `test-repo-git` is the source Git repository, while the various `mozilla-*` are the targets Mercurial repositories to sync to. The syncer will also create its own `firefox-releases` Git repo to work in.

### AMQP Exchange

The AMQP exchange is available at localhost:5672. The RabbitMQ management interface is available at http://localhost:15672/, and the login and password are `guest` (don't do this at home, or in prod).

The `send` container can be used by piping messages to send via the exchange, into `docker compose run --rm -T  send`. The message can also be received with `docker compose run --rm recv`, if the syncer is not running.

### Example synchronisation

To create, then synchronise a new commit to the `beta` and `esr115` branches, do the following. A tag can also be created, and synced.

```console
$ docker compose exec sync git --git-dir /clones/test-repo-git/.git commit --allow-empty -m 'test commit'
$ REV=$(docker compose exec sync git --git-dir /clones/test-repo-git/.git show -q --pretty=format:%H)
$ TAG=FIREFOX_BETA_42_END
$ docker compose exec sync git --git-dir /clones/test-repo-git/.git tag $TAG $REV
$ echo '{"payload": {"type": "push", "repo_url": "/clones/test-repo-git", "branches": { "beta": "'$REV'", "esr115": "'$REV'" }, "tags": { "'$TAG'": "'$REV'" }, "time": "'`date +%s`'", "user": "'$USER'", "push_json_url": "blu", "push_id": 2 }}' \
  | docker compose run --rm -T  send
```

Note that the revision that the tags points to needs to exist on the target Mercurial repo prior to creating it. It can be created as part of the same Pulse message, with the `branches` object.

After successful processing, the new `test commit` should be visible in, e.g.,
the `mozilla-esr115` (and `beta`) repo, and the tag should be present in the `beta` repo.

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

## Configuration

An example configuration file can be found in `config.toml.example`. A different
configuration file can be specified with the `--config` (`-c`) option.

It contains 6 main sections:

- `pulse` holds the exchange configuration (can be overridden by environment, see below)
- `sentry` contains the `sentry_url` for monitoring
- `clones` allows to set the `directory` in which local work clones will be created
- `tracked_repositories` provides `name` and source `url` for Git repos to track
- `branch_mappings` describes which Git repo and branches should be sync to which Hg repo
- `tag_mappings` describes which Git tags should be sync to which Hg repo

By default, `config-docker.toml` will be used, both by the Docker image itself,
as well as the compose stack. It is however possible to instruct the container
to use another of the shipped configuration files by setting the `ENVIRONMENT`
env variable. The container will default to user `config-${ENVIRONMENT}.toml`,
unless the `CMD` is explicitly overridden.

### Repository configuration

Both `*_mappings` sections have a `[source|destination]_url` (`source` is Git, `destination` is Hg). They also have a `[branch|tag]_pattern`, which allows to filter Git branches or tags to sync to specified Hg destinations (and branch). The `pattern` supports regexps.

Note: The tags on the Mercurial side should be created on a dedicated branch. As each tag update requires a new commit to be created, however, this would leave commits on the target Hg branch which do not have equivalents on the Git side. Creating them on a separate branch avoids this confusion. Mercurial will detect them all the same.

```
[[tracked_repositories]]
name = "firefox-releases"
url = "/clones/test-repo-git"

# ESR branches
[[branch_mappings]]
source_url = "/clones/test-repo-git"
branch_pattern = "^(esr\\d+)$"
destination_url = "/clones/mozilla-\\1"
destination_branch = "default"

# ESR tags
[[tag_mappings]]
source_url = "/clones/test-repo-git"
tag_pattern = "^FIREFOX_(\\d+)\\.\\d+\\.\\d+esr_(BUILD\\d+|RELEASE)$"
destination_url = "/clones/mozilla-esr\\1"
tags_destination_branch = "default"
# Default
#tag_message_suffix = "a=tagging CLOSED TREE DONTBUILD"
```

### Pulse parameters

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

### SSH key

If SSH-based authentication is required, the Docker image has an entrypoint that
sets up the necessary environment.

The private key should be pass in a format suitable for `ssh-add`(1) via the
SSH_PRIVATE_KEY environment variable.

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
