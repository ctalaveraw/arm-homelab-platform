#!/usr/bin/env bash
# One reviewed project: use both manifests and the same local configuration.
set -euo pipefail

case "${1:-}" in
    up|run|create|start|restart)
        /usr/local/sbin/caddy-public-check-storage
        ;;
esac

exec /usr/bin/docker-compose \
    --env-file /srv/platform/compose/caddy-public/.env \
    -f /srv/platform/compose/caddy-public/compose.yaml \
    -f /srv/platform/compose/zulip/compose.yaml \
    "$@"
