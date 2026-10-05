#!/usr/bin/env bash
set -euo pipefail

# Always operate relative to the repository root.
cd "$(git rev-parse --show-toplevel)"

IMAGE="platform-hello:ci-$$"
CONTAINER="platform-hello-ci-$$"

RESPONSE=$(mktemp)
CURL_ERROR=$(mktemp)

# Cleanup runs whether the script succeeds or fails.
cleanup() {
    result=$?

    if docker container inspect "$CONTAINER" >/dev/null 2>&1; then
        if (( result != 0 )); then
            echo "=== FAILURE DIAGNOSTICS ===" >&2
            docker logs "$CONTAINER" >&2 || true
            cat "$CURL_ERROR" >&2
        fi

        docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
    fi

    rm -f "$RESPONSE" "$CURL_ERROR"
}

trap cleanup EXIT

echo "=== BUILD ARM64 IMAGE ==="

docker build \
    --platform linux/arm64 \
    -t "$IMAGE" \
    ./apps/platform-hello

echo "=== VERIFY ARCHITECTURE ==="

ARCH=$(docker image inspect \
    --format '{{.Os}}/{{.Architecture}}' \
    "$IMAGE")

test "$ARCH" = "linux/arm64"

echo "=== VERIFY NON-ROOT USER ==="

UID_ACTUAL=$(docker run --rm --entrypoint id "$IMAGE" -u)

test "$UID_ACTUAL" = "10001"

echo "=== START APPLICATION ==="

docker run -d \
    --name "$CONTAINER" \
    -p 127.0.0.1:18082:8080 \
    "$IMAGE"

echo "=== HTTP READINESS CHECK ==="

READY=false

for attempt in $(seq 1 20); do
    echo "Attempt $attempt/20"

    if curl --silent --show-error --fail \
        --max-time 2 \
        http://127.0.0.1:18082/ \
        >"$RESPONSE" 2>"$CURL_ERROR"; then

        READY=true
        break
    fi

    sleep 1
done

if [[ "$READY" != "true" ]]; then
    echo "FAIL: Application did not become ready." >&2
    exit 1
fi

echo "=== VERIFY APPLICATION CONTENT ==="

if ! grep -Fq \
    'Hello from the ARM Homelab Platform!' \
    "$RESPONSE"; then

    echo "FAIL: Unexpected HTTP response content." >&2
    exit 1
fi

echo "PASS: ARM64 Hello World acceptance completed."
