#!/usr/bin/env bash
set -Eeuo pipefail

# Compare the registry manifest digests for two OCI image references.
#
# Equality proves registry manifest identity at inspection time.
# It does not prove source provenance, registry availability, or backup state.
#
# Environment:
#   SOURCE_TLS_VERIFY=true|false
#   DEST_TLS_VERIFY=true|false
#   SOURCE_AUTHFILE=/path/to/auth.json
#   DEST_AUTHFILE=/path/to/auth.json
#
# Usage:
#   verify-oci-parity.sh SOURCE_IMAGE DESTINATION_IMAGE

SOURCE_IMAGE="${1:?Usage: verify-oci-parity.sh SOURCE_IMAGE DESTINATION_IMAGE}"
DESTINATION_IMAGE="${2:?Usage: verify-oci-parity.sh SOURCE_IMAGE DESTINATION_IMAGE}"

SOURCE_TLS_VERIFY="${SOURCE_TLS_VERIFY:-true}"
DEST_TLS_VERIFY="${DEST_TLS_VERIFY:-true}"
SOURCE_AUTHFILE="${SOURCE_AUTHFILE:-}"
DEST_AUTHFILE="${DEST_AUTHFILE:-}"

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

validate_bool() {
    local name="$1"
    local value="$2"

    case "$value" in
        true|false)
            ;;
        *)
            fail "$name must be true or false; got: $value"
            ;;
    esac
}

inspect_digest() {
    local image="$1"
    local tls_verify="$2"
    local authfile="$3"

    local args=(
        inspect
        "--tls-verify=$tls_verify"
        --format '{{.Digest}}'
    )

    if [[ -n "$authfile" ]]; then
        args+=(--authfile "$authfile")
    fi

    skopeo "${args[@]}" "$image"
}

command -v skopeo >/dev/null 2>&1 ||
    fail "skopeo is required"

validate_bool SOURCE_TLS_VERIFY "$SOURCE_TLS_VERIFY"
validate_bool DEST_TLS_VERIFY "$DEST_TLS_VERIFY"

if [[ -n "$SOURCE_AUTHFILE" && ! -f "$SOURCE_AUTHFILE" ]]; then
    fail "Source authfile does not exist: $SOURCE_AUTHFILE"
fi

if [[ -n "$DEST_AUTHFILE" && ! -f "$DEST_AUTHFILE" ]]; then
    fail "Destination authfile does not exist: $DEST_AUTHFILE"
fi

echo "=== OCI REGISTRY PARITY CHECK ==="

SOURCE_DIGEST="$(
    inspect_digest \
        "$SOURCE_IMAGE" \
        "$SOURCE_TLS_VERIFY" \
        "$SOURCE_AUTHFILE"
)" || fail "Unable to inspect source image"

DESTINATION_DIGEST="$(
    inspect_digest \
        "$DESTINATION_IMAGE" \
        "$DEST_TLS_VERIFY" \
        "$DEST_AUTHFILE"
)" || fail "Unable to inspect destination image"

printf '%-21s %s\n' \
    "Source digest:" "$SOURCE_DIGEST" \
    "Destination digest:" "$DESTINATION_DIGEST"

echo

[[ -n "$SOURCE_DIGEST" ]] ||
    fail "Source digest is empty"

[[ -n "$DESTINATION_DIGEST" ]] ||
    fail "Destination digest is empty"

[[ "$SOURCE_DIGEST" == "$DESTINATION_DIGEST" ]] ||
    fail "Registry manifest digests differ"

echo "PASS: Registry manifest identity matches."
