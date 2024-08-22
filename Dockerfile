FROM python:3.12-slim

WORKDIR /app

RUN groupadd --gid 10001 app \
  && useradd -m -g app --uid 10001 -s /usr/sbin/nologin app

RUN apt-get update && \
    apt-get install --yes git mercurial curl vim && \
    apt-get -q --yes autoremove && \
    apt-get clean && \
    rm -rf /root/.cache

# git-cinnabar
COPY install_git-cinnabar.sh .
RUN ./install_git-cinnabar.sh
RUN mv git-cinnabar git-remote-hg /usr/bin/

# install test dependencies
RUN pip install -U pip pytest pytest-mock pytest-cov

# Copy local code to the container image.
COPY . /app
RUN chown -R app: /app

USER app
RUN pip install -e .
