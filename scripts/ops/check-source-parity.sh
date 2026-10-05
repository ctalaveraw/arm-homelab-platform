#!/usr/bin/env bash
set -Eeuo pipefail

# -----------------------------------------------------------------------------
# Compare canonical GitHub main, mirrored Gitea main, and the controller's
# local main branch.
#
# This verifies Git source convergence only.
#
# It does NOT claim parity for:
#   - CI capabilities
#   - secrets
#   - workflow history
#   - registry artifacts
#   - repository settings
#
# Usage:
#
#   bash scripts/ops/check-source-parity.sh
#
# Or, if the remotes have different names:
#
#   bash scripts/ops/check-source-parity.sh <github-remote> <gitea-remote>
# -----------------------------------------------------------------------------

GITHUB_REMOTE="${1:-github}"
GITEA_REMOTE="${2:-gitea}"

die() {
    echo "FAIL: $*" >&2
    exit 1
}

for remote in "$GITHUB_REMOTE" "$GITEA_REMOTE"; do
    if ! git remote get-url "$remote" >/dev/null 2>&1; then
        die "Git remote does not exist: $remote"
    fi
done

REPO_ROOT=$(git rev-parse --show-toplevel) ||
    die "Not inside a Git repository."

cd "$REPO_ROOT"

echo "=== SOURCE PARITY CHECK ==="
echo "Repository: $REPO_ROOT"
echo

echo "Fetching canonical GitHub main..."
git fetch --quiet "$GITHUB_REMOTE" main

echo "Fetching mirrored Gitea main..."
git fetch --quiet "$GITEA_REMOTE" main

LOCAL_MAIN=$(git rev-parse main)
LOCAL_HEAD=$(git rev-parse HEAD)
GITHUB_MAIN=$(git rev-parse "$GITHUB_REMOTE/main")
GITEA_MAIN=$(git rev-parse "$GITEA_REMOTE/main")

printf '%-15s %s\n' \
    "Local main:" "$LOCAL_MAIN" \
    "Local HEAD:" "$LOCAL_HEAD" \
    "GitHub main:" "$GITHUB_MAIN" \
    "Gitea main:" "$GITEA_MAIN"

echo

if [[ "$LOCAL_MAIN" == "$GITHUB_MAIN" ]]; then
    echo "PASS: Local main matches canonical GitHub."
else
    echo "FAIL: Local main differs from canonical GitHub." >&2

    git rev-list \
        --left-right \
        --count \
        "main...$GITHUB_REMOTE/main"

    exit 1
fi

if [[ "$GITEA_MAIN" == "$GITHUB_MAIN" ]]; then
    echo "PASS: Gitea mirror matches canonical GitHub."
else
    echo "FAIL: Gitea mirror differs from canonical GitHub." >&2

    echo
    echo "GitHub/Gitea ahead-behind counts:"
    echo "< GitHub-only commits | > Gitea-only commits"

    git rev-list \
        --left-right \
        --count \
        "$GITHUB_REMOTE/main...$GITEA_REMOTE/main"

    exit 1
fi

echo
echo "PASS: Git source is converged across GitHub, Gitea, and local main."
