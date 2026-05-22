FROM python:3.12-slim

# If DEP_UPDATE is 'yes', don't install the requirements.txt to let pip install the most recent dependencies.
ARG DEP_UPDATE
ENV DEP_UPDATE=$DEP_UPDATE

ENV ENVIRONMENT=docker
ENV SSH_USERNAME=app

ENV PORT=8000

RUN groupadd --gid 10001 app \
  && useradd -m -g app --uid 10001 -d /app -s /usr/sbin/nologin app

RUN apt-get update && \
    apt-get install --yes git mercurial curl tini && \
    apt-get -q --yes autoremove && \
    apt-get clean && \
    rm -rf /root/.cache && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# git-cinnabar
COPY install_git-cinnabar.sh .
RUN ./install_git-cinnabar.sh \
    && mv git-cinnabar git-remote-hg /usr/bin/

RUN --mount=source=./requirements.txt,dst=/app/requirements.txt test "$DEP_UPDATE" = "yes" \
    || pip install -r requirements.txt

RUN mkdir -p /clones \
  && chown app:app /clones

# copy app and install
COPY docker/hgrc /etc/mercurial/hgrc
COPY docker/entrypoint.sh /entrypoint.sh

COPY --chown=app:app . /app
RUN test "$DEP_UPDATE" != "yes" || rm /app/requirements.txt

# Make the install editable so we can mount the local source into a container based on this image.
RUN pip install -e /app[dev]
USER app

HEALTHCHECK CMD curl -sfk http://localhost:$PORT -o/dev/null

# run service
ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]
CMD ["--config", "config-{{ENVIRONMENT}}.toml"]
