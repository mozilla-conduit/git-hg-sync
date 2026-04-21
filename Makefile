DOCKER := $(shell which docker)
DOCKER_COMPOSE := ${DOCKER} compose
ARGS_TESTS ?=

build:
	${DOCKER_COMPOSE} build

format:
	${DOCKER_COMPOSE} run --rm -it --entrypoint bash test -c 'ruff format /app && ruff check --fix /app'

requirements:
	${DOCKER_COMPOSE} run --rm pip-compile

test:
	${DOCKER_COMPOSE} run --rm test ${ARGS_TESTS}
