#!/usr/bin/env bash
set -Eeuo pipefail

# Export an already-built image for transfer between isolated CI jobs.
#
# This script DOES NOT build, test, or scan the image.
# Those stages must already have succeeded before this is called.
#
# Usage:
#   export-image.sh IMAGE OUTPUT_DIRECTORY

IMAGE="${1:?Usage: export-image.sh IMAGE OUTPUT_DIRECTORY}"
OUTDIR="${2:?Usage: export-image.sh IMAGE OUTPUT_DIRECTORY}"

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

docker image inspect "$IMAGE" >/dev/null 2>&1 ||
    fail "Image does not exist: $IMAGE"

mkdir -p "$OUTDIR"

IMAGE_ID_FILE="$OUTDIR/image-id.txt"
IMAGE_TAR="$OUTDIR/image.tar"
CHECKSUM_FILE="$OUTDIR/image.tar.sha256"

# Refuse to overwrite evidence from an earlier run.
for file in \
    "$IMAGE_ID_FILE" \
    "$IMAGE_TAR" \
    "$CHECKSUM_FILE"
do
    [[ ! -e "$file" ]] ||
        fail "Refusing to overwrite existing artifact: $file"
done

cleanup_on_failure() {
    result=$?

    if (( result != 0 )); then
        rm -f \
            "$IMAGE_ID_FILE" \
            "$IMAGE_TAR" \
            "$CHECKSUM_FILE"
    fi

    exit "$result"
}

trap cleanup_on_failure EXIT


echo "=== RECORD DOCKER IMAGE ID ==="

(
    set -o noclobber

    docker image inspect \
        --format '{{.Id}}' \
        "$IMAGE" \
        > "$IMAGE_ID_FILE"
)

cat "$IMAGE_ID_FILE"


echo
echo "=== EXPORT IMAGE ==="

(
    set -o noclobber

    docker save "$IMAGE" \
        > "$IMAGE_TAR"
)


echo
echo "=== RECORD TRANSFER CHECKSUM ==="

(
    cd "$OUTDIR"
    set -o noclobber

    sha256sum image.tar \
        > image.tar.sha256
)

cat "$CHECKSUM_FILE"


trap - EXIT

echo
echo "PASS: Exported verified CI image artifact."
