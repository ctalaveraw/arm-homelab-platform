#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

IMAGE="${1:?Usage: test-hello.sh <image-reference>}"
CONTAINER="platform-hello-ci-$$"

RESPONSE=$(mktemp)
CURL_ERROR=$(mktemp)

cleanup() {
    result=$?

    if docker container inspect "$CONTAINER" >/dev/null 2>&1; then
        if (( result != 0 )); then
            echo "=== FAILURE DIAGNOSTICS ===" >&2
            docker logs "$CONTAINER" >&2 || true

            if [[ -s "$CURL_ERROR" ]]; then
                echo "=== LAST CURL ERROR ===" >&2
                cat "$CURL_ERROR" >&2
            fi
        fi

        docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
    fi

    rm -f "$RESPONSE" "$CURL_ERROR"

    trap - EXIT
    exit "$result"
}

trap cleanup EXIT

echo "=== VERIFY IMAGE EXISTS ==="
echo "Image: $IMAGE"

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    echo "FAIL: Expected image does not exist: $IMAGE" >&2
    exit 1
fi

echo "=== VERIFY ARCHITECTURE ==="

ARCH=$(docker image inspect \
    --format '{{.Os}}/{{.Architecture}}' \
    "$IMAGE")

echo "Architecture: $ARCH"
test "$ARCH" = "linux/arm64"

echo "=== VERIFY NON-ROOT USER ==="

UID_ACTUAL=$(docker run --rm \
    --entrypoint id \
    "$IMAGE" \
    -u)

echo "Runtime UID: $UID_ACTUAL"
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

    if curl \
        --silent \
        --show-error \
        --fail \
        --max-time 2 \
        http://127.0.0.1:18082/ \
        >"$RESPONSE" \
        2>"$CURL_ERROR"; then

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

echo "PASS: ARM64 Hello World acceptance completed for $IMAGE"
