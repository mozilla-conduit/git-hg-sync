ARGS_BUILD ?=
ARGS_TESTS ?=

DOCKER := $(shell which docker)
DOCKER_COMPOSE := ${DOCKER} compose

build:
	${DOCKER_COMPOSE} build ${ARGS_BUILD}

format:
	${DOCKER_COMPOSE} run --rm -it --entrypoint bash test -c 'ruff format /app && ruff check --fix /app'

OUTPUT_DIRECTORY=new-requirements
requirements:
	${MAKE} build ARGS_BUILD=pip-compile
	mkdir -p ${OUTPUT_DIRECTORY}
	${DOCKER_COMPOSE} run --rm --volume ./${OUTPUT_DIRECTORY}:/app/${OUTPUT_DIRECTORY}:z pip-compile
	mv new-requirements/requirements.txt requirements.txt
	rmdir ${OUTPUT_DIRECTORY}
	${MAKE} build
	${MAKE} test

test:
	${DOCKER_COMPOSE} run --rm test ${ARGS_TESTS}
