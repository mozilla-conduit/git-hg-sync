FROM python:3.12-slim

WORKDIR /app

RUN groupadd --gid 10001 app \
  && useradd -m -g app --uid 10001 -s /usr/sbin/nologin app

RUN apt-get update && \
    apt-get install --yes git && \
    apt-get -q --yes autoremove && \
    apt-get clean && \
    rm -rf /root/.cache

# install test dependencies
RUN pip install -U pip pytest pytest-mock

# Copy local code to the container image.
COPY . /app

USER app
RUN pip install -e .
