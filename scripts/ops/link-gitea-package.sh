#!/usr/bin/env bash
set -Eeuo pipefail

# Link an already-published Gitea package to a Gitea repository.
#
# This changes Gitea package metadata only. It does not alter the OCI artifact.
#
# Authentication:
#   GITEA_TOKEN must be supplied by the caller.
#
# Usage:
#   link-gitea-package.sh \
#       GITEA_BASE_URL OWNER PACKAGE_TYPE PACKAGE_NAME REPOSITORY_NAME

GITEA_BASE_URL="${1:?Usage: link-gitea-package.sh GITEA_BASE_URL OWNER PACKAGE_TYPE PACKAGE_NAME REPOSITORY_NAME}"
OWNER="${2:?Usage: link-gitea-package.sh GITEA_BASE_URL OWNER PACKAGE_TYPE PACKAGE_NAME REPOSITORY_NAME}"
PACKAGE_TYPE="${3:?Usage: link-gitea-package.sh GITEA_BASE_URL OWNER PACKAGE_TYPE PACKAGE_NAME REPOSITORY_NAME}"
PACKAGE_NAME="${4:?Usage: link-gitea-package.sh GITEA_BASE_URL OWNER PACKAGE_TYPE PACKAGE_NAME REPOSITORY_NAME}"
REPOSITORY_NAME="${5:?Usage: link-gitea-package.sh GITEA_BASE_URL OWNER PACKAGE_TYPE PACKAGE_NAME REPOSITORY_NAME}"

GITEA_TOKEN="${GITEA_TOKEN:-}"

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

command -v curl >/dev/null 2>&1 ||
    fail "curl is required"

command -v python3 >/dev/null 2>&1 ||
    fail "python3 is required"

[[ -n "$GITEA_TOKEN" ]] ||
    fail "GITEA_TOKEN is not set"

case "$GITEA_BASE_URL" in
    http://*|https://*)
        ;;
    *)
        fail "GITEA_BASE_URL must begin with http:// or https://"
        ;;
esac

for value in \
    "$OWNER" \
    "$PACKAGE_TYPE" \
    "$PACKAGE_NAME" \
    "$REPOSITORY_NAME"
do
    [[ "$value" =~ ^[A-Za-z0-9._-]+$ ]] ||
        fail "Unsupported path component: $value"
done

TMP_DIR="$(mktemp -d)" ||
    fail "Unable to create temporary directory"

CURL_CONFIG="${TMP_DIR}/curl.conf"
RESPONSE_BODY="${TMP_DIR}/response"

cleanup() {
    rm -rf "$TMP_DIR"
}

trap cleanup EXIT

umask 077

printf 'header = "Authorization: token %s"\n' \
    "$GITEA_TOKEN" \
    > "$CURL_CONFIG"

PACKAGE_URL="$(
    printf '%s/api/v1/packages/%s/%s/%s' \
        "${GITEA_BASE_URL%/}" \
        "$OWNER" \
        "$PACKAGE_TYPE" \
        "$PACKAGE_NAME"
)"

LINK_URL="$(
    printf '%s/-/link/%s' \
        "$PACKAGE_URL" \
        "$REPOSITORY_NAME"
)"

echo "=== LINK GITEA PACKAGE ==="
echo "Package    : ${OWNER}/${PACKAGE_TYPE}/${PACKAGE_NAME}"
echo "Repository : ${OWNER}/${REPOSITORY_NAME}"

echo
echo "=== CHECK CURRENT PACKAGE LINK ==="

STATUS="$(
    curl \
        --silent \
        --show-error \
        --config "$CURL_CONFIG" \
        --request GET \
        --output "$RESPONSE_BODY" \
        --write-out '%{http_code}' \
        "$PACKAGE_URL"
)" || fail "Gitea package-state request failed"

[[ "$STATUS" == "200" ]] ||
    fail "Expected HTTP 200 while reading package state; received HTTP $STATUS"

LINK_STATE="$(
    python3 - \
        "$RESPONSE_BODY" \
        "$OWNER" \
        "$REPOSITORY_NAME" <<'PY_STATE'
import json
import sys

response_path, owner, repository_name = sys.argv[1:]
target = f"{owner}/{repository_name}"

with open(response_path) as stream:
    versions = json.load(stream)

if not isinstance(versions, list) or not versions:
    raise SystemExit("Package version list is empty or invalid")

repositories = set()

for version in versions:
    repository = version.get("repository")

    if repository is None:
        continue

    if not isinstance(repository, dict):
        raise SystemExit("Unexpected package repository metadata")

    full_name = repository.get("full_name")

    if not full_name:
        repo_name = repository.get("name")
        repo_owner = repository.get("owner") or {}
        owner_name = (
            repo_owner.get("login")
            or repo_owner.get("username")
        )

        if owner_name and repo_name:
            full_name = f"{owner_name}/{repo_name}"

    if not full_name:
        raise SystemExit("Unable to identify linked repository")

    repositories.add(full_name)

if not repositories:
    print("unlinked")
elif repositories == {target}:
    print("linked")
else:
    print("mismatch:" + ",".join(sorted(repositories)))
PY_STATE
)" || fail "Unable to interpret Gitea package metadata"

case "$LINK_STATE" in
    linked)
        echo "PASS: Package is already linked to the requested repository."
        exit 0
        ;;
    unlinked)
        echo "Package is currently unlinked; creating association."
        ;;
    mismatch:*)
        fail "Package is linked to a different repository: ${LINK_STATE#mismatch:}"
        ;;
    *)
        fail "Unexpected package link state: $LINK_STATE"
        ;;
esac

echo
echo "=== CREATE PACKAGE LINK ==="

STATUS="$(
    curl \
        --silent \
        --show-error \
        --config "$CURL_CONFIG" \
        --request POST \
        --output "$RESPONSE_BODY" \
        --write-out '%{http_code}' \
        "$LINK_URL"
)" || fail "Gitea package-link request failed"

if [[ "$STATUS" != "201" ]]; then
    echo "Gitea response:" >&2
    cat "$RESPONSE_BODY" >&2
    fail "Expected HTTP 201, received HTTP $STATUS"
fi

echo
echo "PASS: Gitea package linked to repository."
