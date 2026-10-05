#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

IMAGE="${1:?Usage: build-hello.sh <image-reference>}"

echo "=== BUILD ARM64 HELLO IMAGE ==="
echo "Image: $IMAGE"

docker build \
    --platform linux/arm64 \
    -t "$IMAGE" \
    ./apps/platform-hello

echo "PASS: Built $IMAGE"
