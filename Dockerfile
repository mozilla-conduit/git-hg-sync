FROM python:3.12-slim

RUN groupadd --gid 10001 app \
  && useradd -m -g app --uid 10001 -d /app -s /usr/sbin/nologin app

RUN apt-get update && \
    apt-get install --yes git mercurial curl vim && \
    apt-get -q --yes autoremove && \
    apt-get clean && \
    rm -rf /root/.cache && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# git-cinnabar
COPY install_git-cinnabar.sh .
RUN ./install_git-cinnabar.sh \
    && mv git-cinnabar git-remote-hg /usr/bin/

# install test dependencies
RUN pip install -U pip pytest pytest-mock pip-tools

# setup just the venv so changes to the source won't require a full venv
# rebuild
COPY --chown=app:app README.md .
COPY --chown=app:app pyproject.toml .
RUN pip-compile --verbose pyproject.toml \
    && pip install -r requirements.txt

RUN echo '[ui]\nssh = ssh -oStrictHostKeyChecking=accept-new' >> /etc/mercurial/hgrc \
  && mkdir -p /clones \
  && chown app:app /clones

# copy app and install
COPY --chown=app:app . /app
COPY --chown=app:app entrypoint.sh /entrypoint.sh
# Make the install editable so we can mount the local source into a container based on this image.
RUN pip install -e /app
USER app

ENTRYPOINT ["/entrypoint.sh"]
CMD ["--config", "config-docker.toml"]
