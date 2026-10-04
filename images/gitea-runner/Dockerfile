FROM docker.io/gitea/runner:3

# Validation tooling, not a Docker daemon.
RUN apk add --no-cache \
    bash \
    ca-certificates \
    git \
    nodejs \
    npm \
    python3 \
    py3-pip \
    py3-virtualenv \
    shellcheck \
    docker-cli \
    docker-cli-compose

# Fail the image build early if portable CI bootstrap cannot work.
RUN python3 -m venv /tmp/venv-probe \
    && /tmp/venv-probe/bin/python -m pip --version \
    && rm -rf /tmp/venv-probe

# Keep the user home separate from the upstream /data volume.
RUN addgroup -S -g 10001 ci \
    && adduser -S -D -u 10001 -h /home/ci -G ci ci \
    && mkdir -p /home/ci /workspace \
    && chown -R ci:ci /home/ci /workspace

ENV HOME=/home/ci
WORKDIR /data
USER ci

ENTRYPOINT ["/usr/local/bin/gitea-runner"]
CMD ["daemon"]
