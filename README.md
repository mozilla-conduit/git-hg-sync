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

The AMQP exchange is available at localhost:5672. To send a message, you can do the following

```console
$ echo '{"payload": {"type": "push", "repo_url": "bla", "branches": [ "main" ], "tags": [], "time": "'`date +%s`'", "user": "'$USER'", "push_json_url": "blu", "pushid": 2 }}' \
  | docker compose run --rm -T  send
```

(The message can also be received with `docker compose run --rm recv`.)

The RabbitMQ management interface is available at http://localhost:15672/, and
the login and password are `guest` (don't do this at home, or in prod).

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
