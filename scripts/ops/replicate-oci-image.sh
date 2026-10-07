#!/usr/bin/env bash
set -Eeuo pipefail

# Copy an existing OCI image between registries without rebuilding it.
#
# The source and destination must use docker:// transport.
# Registry credentials are supplied externally through optional authfiles.
#
# Environment:
#   SOURCE_TLS_VERIFY=true|false
#   DEST_TLS_VERIFY=true|false
#   SOURCE_AUTHFILE=/path/to/auth.json
#   DEST_AUTHFILE=/path/to/auth.json
#
# Usage:
#   replicate-oci-image.sh SOURCE_IMAGE DESTINATION_IMAGE

SOURCE_IMAGE="${1:?Usage: replicate-oci-image.sh SOURCE_IMAGE DESTINATION_IMAGE}"
DESTINATION_IMAGE="${2:?Usage: replicate-oci-image.sh SOURCE_IMAGE DESTINATION_IMAGE}"

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

command -v skopeo >/dev/null 2>&1 ||
    fail "skopeo is required"

[[ "$SOURCE_IMAGE" == docker://* ]] ||
    fail "Source must use docker:// transport: $SOURCE_IMAGE"

[[ "$DESTINATION_IMAGE" == docker://* ]] ||
    fail "Destination must use docker:// transport: $DESTINATION_IMAGE"

validate_bool SOURCE_TLS_VERIFY "$SOURCE_TLS_VERIFY"
validate_bool DEST_TLS_VERIFY "$DEST_TLS_VERIFY"

if [[ -n "$SOURCE_AUTHFILE" && ! -f "$SOURCE_AUTHFILE" ]]; then
    fail "Source authfile does not exist: $SOURCE_AUTHFILE"
fi

if [[ -n "$DEST_AUTHFILE" && ! -f "$DEST_AUTHFILE" ]]; then
    fail "Destination authfile does not exist: $DEST_AUTHFILE"
fi

SKOPEO_ARGS=(
    copy
    --preserve-digests
    "--src-tls-verify=$SOURCE_TLS_VERIFY"
    "--dest-tls-verify=$DEST_TLS_VERIFY"
)

if [[ -n "$SOURCE_AUTHFILE" ]]; then
    SKOPEO_ARGS+=(--src-authfile "$SOURCE_AUTHFILE")
fi

if [[ -n "$DEST_AUTHFILE" ]]; then
    SKOPEO_ARGS+=(--dest-authfile "$DEST_AUTHFILE")
fi

echo "=== REPLICATE OCI IMAGE ==="
echo "Source      : $SOURCE_IMAGE"
echo "Destination : $DESTINATION_IMAGE"
echo

skopeo "${SKOPEO_ARGS[@]}" \
    "$SOURCE_IMAGE" \
    "$DESTINATION_IMAGE"

echo
echo "PASS: OCI image replicated without rebuild."
