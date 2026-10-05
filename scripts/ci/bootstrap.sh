#!/usr/bin/env bash

# -----------------------------------------------------------------------------
# ARM Homelab Platform - CI Dependency Bootstrap
#
# Purpose:
#   Ensure the repository-local CI toolchain exists and contains every tool
#   required by scripts/ci/validate.sh.
#
# Important design rule:
#
#   The existence of .ci-venv does NOT mean its dependencies are current.
#
# An older implementation only installed dependencies when the virtual
# environment was first created. That caused dependency drift:
#
#   .ci-venv existed
#       +
#   Ansible existed
#       +
#   new validators were added
#       =
#   validate.sh expected tools that bootstrap.sh never installed
#
# This script therefore separates:
#
#   1. creating the virtual environment when necessary
#   2. converging its required dependencies on EVERY bootstrap execution
#
# pip itself is idempotent enough for this purpose: packages already satisfying
# the pinned constraints are reused rather than blindly reinstalled.
# -----------------------------------------------------------------------------

set -Eeuo pipefail


# -----------------------------------------------------------------------------
# Optional debugging
#
# Usage:
#
#   CI_DEBUG=true bash scripts/ci/bootstrap.sh
#
# Useful when Python/pip/package installation behaves differently between
# local ARM64, GitHub-hosted CI, and the Gitea runner.
# -----------------------------------------------------------------------------

if [[ "${CI_DEBUG:-false}" == "true" ]]; then
    export PS4='+ ${BASH_SOURCE}:${LINENO}:${FUNCNAME[0]:-main}: '
    set -x
fi


# -----------------------------------------------------------------------------
# Error diagnostics
# -----------------------------------------------------------------------------

on_error() {
    local exit_code="$1"
    local line_number="$2"
    local command="$3"

    trap - ERR

    {
        echo
        echo "================================================================"
        echo "CI BOOTSTRAP FAILED"
        echo "================================================================"
        echo "Exit code : $exit_code"
        echo "Line      : $line_number"
        echo "Command   : $command"
        echo "PWD       : $PWD"
        echo "Git HEAD  : $(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
        echo "Python    : $(python3 --version 2>&1 || echo unavailable)"
        echo "================================================================"
    } >&2

    exit "$exit_code"
}

trap 'on_error "$?" "$LINENO" "$BASH_COMMAND"' ERR


die() {
    echo "FAIL: $*" >&2
    exit 1
}


# -----------------------------------------------------------------------------
# Repository root
# -----------------------------------------------------------------------------

REPO_ROOT=$(git rev-parse --show-toplevel) ||
    die "This script must run inside a Git repository."

cd "$REPO_ROOT"

echo "=== CI DEPENDENCY BOOTSTRAP ==="
echo "Repository : $REPO_ROOT"
echo "Git HEAD   : $(git rev-parse --short HEAD)"
echo "Python     : $(python3 --version)"


# -----------------------------------------------------------------------------
# Host prerequisite
# -----------------------------------------------------------------------------

command -v python3 >/dev/null 2>&1 ||
    die "python3 is required but unavailable."


# -----------------------------------------------------------------------------
# Virtual environment
#
# Only environment creation is conditional.
#
# Dependency installation below is deliberately NOT inside this condition.
# -----------------------------------------------------------------------------

if [[ ! -x .ci-venv/bin/python ]]; then
    echo
    echo "=== CREATE CI VIRTUAL ENVIRONMENT ==="

    python3 -m venv .ci-venv
else
    echo
    echo "CI virtual environment already exists."
fi


# -----------------------------------------------------------------------------
# Verify pip before attempting package convergence
# -----------------------------------------------------------------------------

if ! .ci-venv/bin/python -m pip --version >/dev/null 2>&1; then
    die "pip is unavailable inside .ci-venv."
fi


# -----------------------------------------------------------------------------
# Python CI toolchain
#
# Keep these versions explicit so local ARM64, GitHub Actions, and Gitea
# validation do not silently drift onto unrelated tool releases.
#
# Every execution checks that the requested package set is satisfied.
# -----------------------------------------------------------------------------

echo
echo "=== CONVERGE CI PYTHON DEPENDENCIES ==="

.ci-venv/bin/python -m pip install \
    --disable-pip-version-check \
    'ansible-core==2.21.4' \
    'PyYAML>=6,<7' \
    'ruff==0.16.10' \
    'yamllint==1.38.0' \
    'actionlint-py==1.7.12.25'


# -----------------------------------------------------------------------------
# ShellCheck
#
# ShellCheck is managed differently because it is a native executable rather
# than part of our Python virtual environment.
#
# The R5C already gets ShellCheck through the Ansible common package baseline.
# GitHub-hosted CI may need bootstrap.sh to install it.
# -----------------------------------------------------------------------------

if command -v shellcheck >/dev/null 2>&1; then
    echo
    echo "ShellCheck already available: $(shellcheck --version | awk '/version:/ {print $2}')"
elif [[ "${CI:-false}" == "true" ]]; then
    echo
    echo "=== INSTALL SHELLCHECK FOR HOSTED CI ==="

    sudo apt-get update -qq
    sudo apt-get install -y -qq shellcheck
else
    echo
    echo "WARN: ShellCheck is not installed on this local host." >&2
    echo "      validate.sh will warn locally and require it in CI." >&2
fi


# -----------------------------------------------------------------------------
# Post-bootstrap verification
#
# Do not simply print "ready." Prove that the executables expected by
# validate.sh actually exist.
# -----------------------------------------------------------------------------

echo
echo "=== VERIFY CI TOOLCHAIN ==="

REQUIRED_EXECUTABLES=(
    .ci-venv/bin/python
    .ci-venv/bin/ansible-playbook
    .ci-venv/bin/ruff
    .ci-venv/bin/yamllint
    .ci-venv/bin/actionlint
)

for executable in "${REQUIRED_EXECUTABLES[@]}"; do
    if [[ ! -x "$executable" ]]; then
        die "Expected CI executable is missing after bootstrap: $executable"
    fi

    printf 'PASS: %s\n' "$executable"
done


# -----------------------------------------------------------------------------
# Print versions.
#
# This makes CI logs much more useful when debugging environment divergence.
# -----------------------------------------------------------------------------

echo
echo "=== CI TOOL VERSIONS ==="

.ci-venv/bin/python --version
.ci-venv/bin/ansible-playbook --version | head -n 1
.ci-venv/bin/ruff --version
.ci-venv/bin/yamllint --version
.ci-venv/bin/actionlint --version

if command -v shellcheck >/dev/null 2>&1; then
    shellcheck --version | grep -E '^(version|shellcheck)'
fi

echo
echo "PASS: CI dependencies converged."
