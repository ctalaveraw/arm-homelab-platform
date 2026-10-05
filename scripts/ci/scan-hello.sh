#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

IMAGE="${1:?Usage: scan-hello.sh <image-reference>}"

echo "=== VERIFY IMAGE EXISTS ==="
echo "Image: $IMAGE"

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    echo "FAIL: Expected image does not exist: $IMAGE" >&2
    exit 1
fi

if ! command -v trivy >/dev/null 2>&1; then
    echo "FAIL: Trivy is not installed." >&2
    exit 1
fi

echo
echo "=== SECURITY FINDINGS ==="

# Visibility pass: show the complete vulnerability/secret baseline.
# Findings are reported but do not fail this command.
trivy image \
    --scanners vuln,secret \
    --severity UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL \
    --exit-code 0 \
    --no-progress \
    "$IMAGE"

echo
echo "=== CRITICAL SECURITY GATE ==="

# Promotion gate: critical findings stop the pipeline.
trivy image \
    --scanners vuln,secret \
    --severity CRITICAL \
    --exit-code 1 \
    --no-progress \
    "$IMAGE"

echo
echo "PASS: Security gate passed for $IMAGE"
