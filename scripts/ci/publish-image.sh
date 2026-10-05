#!/usr/bin/env bash
set -Eeuo pipefail

# Publish an already-verified local image.
#
# Registry authentication deliberately does NOT happen here.
# Credential handling belongs to the CI execution environment.
#
# This script performs no rebuild.
#
# Usage:
#   publish-image.sh LOCAL_IMAGE TARGET_IMAGE

LOCAL_IMAGE="${1:?Usage: publish-image.sh LOCAL_IMAGE TARGET_IMAGE}"
TARGET_IMAGE="${2:?Usage: publish-image.sh LOCAL_IMAGE TARGET_IMAGE}"

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

docker image inspect "$LOCAL_IMAGE" >/dev/null 2>&1 ||
    fail "Local image does not exist: $LOCAL_IMAGE"


echo "=== TAG VERIFIED IMAGE ==="

docker tag \
    "$LOCAL_IMAGE" \
    "$TARGET_IMAGE"


echo
echo "=== PUSH VERIFIED IMAGE ==="

docker push "$TARGET_IMAGE"


echo
echo "PASS: Published $TARGET_IMAGE"
