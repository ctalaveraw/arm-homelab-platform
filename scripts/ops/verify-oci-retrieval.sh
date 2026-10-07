#!/usr/bin/env bash
set -Eeuo pipefail

# Prove that a registry can serve the complete referenced OCI artifact.
#
# The image is copied into a fresh temporary OCI layout and then discarded.
# This tests retrieval of the manifest, config, and referenced blobs.
#
# It intentionally does NOT compare the temporary OCI-layout digest with the
# source registry digest because transport representation may differ.
#
# Environment:
#   TLS_VERIFY=true|false
#   AUTHFILE=/path/to/auth.json
#
# Usage:
#   verify-oci-retrieval.sh IMAGE

IMAGE="${1:?Usage: verify-oci-retrieval.sh IMAGE}"

TLS_VERIFY="${TLS_VERIFY:-true}"
AUTHFILE="${AUTHFILE:-}"

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

case "$TLS_VERIFY" in
    true|false)
        ;;
    *)
        fail "TLS_VERIFY must be true or false; got: $TLS_VERIFY"
        ;;
esac

command -v skopeo >/dev/null 2>&1 ||
    fail "skopeo is required"

if [[ -n "$AUTHFILE" && ! -f "$AUTHFILE" ]]; then
    fail "Authfile does not exist: $AUTHFILE"
fi

PULL_DIR="$(mktemp -d)" ||
    fail "Unable to create temporary OCI directory"

cleanup() {
    rm -rf "$PULL_DIR"
}

trap cleanup EXIT

INSPECT_ARGS=(
    inspect
    "--tls-verify=$TLS_VERIFY"
    --format '{{.Digest}}'
)

COPY_ARGS=(
    copy
    "--src-tls-verify=$TLS_VERIFY"
)

if [[ -n "$AUTHFILE" ]]; then
    INSPECT_ARGS+=(--authfile "$AUTHFILE")
    COPY_ARGS+=(--src-authfile "$AUTHFILE")
fi

echo "=== VERIFY OCI RETRIEVAL ==="
echo "Image: $IMAGE"

DIGEST="$(
    skopeo "${INSPECT_ARGS[@]}" "$IMAGE"
)" || fail "Unable to inspect image"

echo "Registry digest: $DIGEST"
echo

skopeo "${COPY_ARGS[@]}" \
    "$IMAGE" \
    "oci:${PULL_DIR}:artifact"

echo
echo "PASS: Complete OCI artifact was retrieved into a fresh layout."
