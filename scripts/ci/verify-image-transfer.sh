#!/usr/bin/env bash
set -Eeuo pipefail

# Verify and load an image transferred from another CI job.
#
# Two different integrity questions are answered:
#
#   1. Did the archive bytes change?
#        -> SHA-256 checksum
#
#   2. Did Docker reconstruct the same image we originally exported?
#        -> Docker image ID comparison
#
# Usage:
#   verify-image-transfer.sh IMAGE ARTIFACT_DIRECTORY

IMAGE="${1:?Usage: verify-image-transfer.sh IMAGE ARTIFACT_DIRECTORY}"
ARTIFACT_DIR="${2:?Usage: verify-image-transfer.sh IMAGE ARTIFACT_DIRECTORY}"

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

IMAGE_ID_FILE="$ARTIFACT_DIR/image-id.txt"
IMAGE_TAR="$ARTIFACT_DIR/image.tar"
CHECKSUM_FILE="$ARTIFACT_DIR/image.tar.sha256"

for file in \
    "$IMAGE_ID_FILE" \
    "$IMAGE_TAR" \
    "$CHECKSUM_FILE"
do
    [[ -f "$file" ]] ||
        fail "Required transfer artifact is missing: $file"
done


echo "=== VERIFY ARCHIVE CHECKSUM ==="

(
    cd "$ARTIFACT_DIR"
    sha256sum --check image.tar.sha256
)


EXPECTED_IMAGE_ID=$(< "$IMAGE_ID_FILE")

echo
echo "Expected Docker image ID:"
echo "$EXPECTED_IMAGE_ID"


echo
echo "=== LOAD TRANSFERRED IMAGE ==="

docker load \
    --input "$IMAGE_TAR"


docker image inspect "$IMAGE" >/dev/null 2>&1 ||
    fail "Expected image reference was not restored: $IMAGE"


ACTUAL_IMAGE_ID=$(
    docker image inspect \
        --format '{{.Id}}' \
        "$IMAGE"
)


echo
echo "Loaded Docker image ID:"
echo "$ACTUAL_IMAGE_ID"


if [[ "$ACTUAL_IMAGE_ID" != "$EXPECTED_IMAGE_ID" ]]; then
    fail "Loaded image identity differs from tested/scanned image"
fi


echo
echo "PASS: Transferred image identity preserved."
