#!/usr/bin/env bash

# -----------------------------------------------------------------------------
# ARM Homelab Platform - Repository Validation
#
# Purpose:
#   Run the repository's portable/static validation contract before we allow
#   application build, scan, publication, or deployment work to proceed.
#
# Design goals:
#   - Fail fast on validation errors.
#   - Print enough context that a CI failure can be diagnosed from the log.
#   - Use the repository-managed .ci-venv when available.
#   - Discover tracked files from Git rather than maintaining duplicate lists.
#   - Never require real secrets to render Compose configuration.
#
# Optional debugging:
#
#   CI_DEBUG=true bash scripts/ci/validate.sh
#
# This enables Bash xtrace with source file + line-number information.
# Do NOT enable this around commands that could contain secrets.
# -----------------------------------------------------------------------------

set -Eeuo pipefail

# Add useful source/line information if explicit debugging is requested.
if [[ "${CI_DEBUG:-false}" == "true" ]]; then
    export PS4='+ ${BASH_SOURCE}:${LINENO}:${FUNCNAME[0]:-main}: '
    set -x
fi


# -----------------------------------------------------------------------------
# Error reporting
#
# The ERR trap gives us useful context when an unexpected command returns
# nonzero under `set -e`.
#
# Note:
#   Commands intentionally used as conditions inside `if`, `while`, etc. do
#   not necessarily invoke ERR. Those branches should print their own errors.
# -----------------------------------------------------------------------------

on_error() {
    local exit_code="$1"
    local line_number="$2"
    local command="$3"

    # Prevent recursive ERR traps if diagnostic output itself encounters trouble.
    trap - ERR

    {
        echo
        echo "================================================================"
        echo "VALIDATION FAILED"
        echo "================================================================"
        echo "Exit code : $exit_code"
        echo "Line      : $line_number"
        echo "Command   : $command"
        echo "PWD       : $PWD"
        echo "Git HEAD  : $(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
        echo "================================================================"
    } >&2

    exit "$exit_code"
}

trap 'on_error "$?" "$LINENO" "$BASH_COMMAND"' ERR


# -----------------------------------------------------------------------------
# Small helpers
# -----------------------------------------------------------------------------

section() {
    echo
    echo "================================================================"
    echo "$1"
    echo "================================================================"
}

die() {
    echo "FAIL: $*" >&2
    exit 1
}

# Validate either:
#   - an executable path such as .ci-venv/bin/ruff
#   - a normal PATH command such as python3
require_command() {
    local command_name="$1"

    if [[ "$command_name" == */* ]]; then
        [[ -x "$command_name" ]] ||
            die "Required executable is missing: $command_name"
    else
        command -v "$command_name" >/dev/null 2>&1 ||
            die "Required command is unavailable in PATH: $command_name"
    fi
}


# -----------------------------------------------------------------------------
# Repository root
#
# Always validate from Git's top-level directory so execution behaves the same
# whether called from /srv/platform, scripts/ci/, or a CI checkout.
# -----------------------------------------------------------------------------

REPO_ROOT=$(git rev-parse --show-toplevel) ||
    die "This script must run inside a Git repository."

cd "$REPO_ROOT"

echo "=== PLATFORM VALIDATION ==="
echo "Repository   : $REPO_ROOT"
echo "Architecture : $(uname -m)"
echo "Git HEAD     : $(git rev-parse --short HEAD)"


# -----------------------------------------------------------------------------
# Tool selection
#
# bootstrap.sh creates .ci-venv and installs the pinned CI Python toolchain.
#
# If that environment exists, use it consistently.
# Otherwise, fall back to host-installed tools for developer convenience.
#
# CI itself should normally have run:
#
#   bash scripts/ci/bootstrap.sh
#
# before this validation script.
# -----------------------------------------------------------------------------

if [[ -x .ci-venv/bin/python ]]; then
    echo "Tool source  : repository .ci-venv"

    PYTHON=.ci-venv/bin/python
    ANSIBLE=.ci-venv/bin/ansible-playbook
    RUFF=.ci-venv/bin/ruff
    YAMLLINT=.ci-venv/bin/yamllint
    ACTIONLINT=.ci-venv/bin/actionlint
else
    echo "Tool source  : host PATH"

    PYTHON=python3
    ANSIBLE=ansible-playbook
    RUFF=ruff
    YAMLLINT=yamllint
    ACTIONLINT=actionlint
fi

# Fail here with a useful message rather than 50 lines later with:
#   "No such file or directory"
require_command "$PYTHON"
require_command "$ANSIBLE"
require_command "$RUFF"
require_command "$YAMLLINT"
require_command "$ACTIONLINT"


# -----------------------------------------------------------------------------
# Bash syntax + ShellCheck
#
# Discover every tracked shell script under scripts/.
#
# Why Git-tracked files?
#   CI validates committed repository state, not random untracked local files.
# -----------------------------------------------------------------------------

section "SHELL SYNTAX AND LINT"

mapfile -d '' SHELL_FILES < <(
    git ls-files -z \
        'scripts/*.sh' \
        'scripts/**/*.sh'
)

if (( ${#SHELL_FILES[@]} == 0 )); then
    echo "No tracked shell scripts found."
else
    echo "Shell files: ${#SHELL_FILES[@]}"

    echo
    echo "--- bash -n ---"
    bash -n "${SHELL_FILES[@]}"

    echo
    echo "--- ShellCheck ---"

    if command -v shellcheck >/dev/null 2>&1; then
        shellcheck "${SHELL_FILES[@]}"
    elif [[ "${CI:-false}" == "true" ]]; then
        die "ShellCheck is required in CI but is unavailable."
    else
        echo "WARN: ShellCheck unavailable locally; Bash syntax passed." >&2
    fi
fi


# -----------------------------------------------------------------------------
# Lightweight Python + YAML parse validation
#
# This catches malformed input before the more opinionated linters execute.
#
# Python:
#   Our storage guards are parsed with Python's AST.
#
# YAML:
#   Every tracked *.yml / *.yaml file must parse successfully.
#
# This is syntax validation, NOT style linting. yamllint runs later.
# -----------------------------------------------------------------------------

section "PYTHON AND YAML PARSE VALIDATION"

"$PYTHON" <<'PY'
import ast
import subprocess
from pathlib import Path


try:
    import yaml
except ImportError as exc:
    raise SystemExit(
        "FAIL: PyYAML is unavailable. Run scripts/ci/bootstrap.sh first."
    ) from exc


tracked = [
    Path(item)
    for item in subprocess.check_output(
        ["git", "ls-files", "--cached", "-z"]
    ).decode().split("\0")
    if item
]


python_count = 0
yaml_count = 0


for path in tracked:
    # Storage guards are security/reliability-sensitive Python artifacts.
    # Parse each guard before later Ruff linting.
    if path.name == "check-storage.py":
        ast.parse(
            path.read_text(),
            filename=str(path),
        )

        python_count += 1
        print(f"PASS Python parse: {path}")

    # Parse all tracked YAML, including:
    #   - GitHub Actions
    #   - Gitea Actions
    #   - Ansible
    #   - Compose
    if path.suffix in {".yml", ".yaml"}:
        with path.open() as stream:
            list(yaml.safe_load_all(stream))

        yaml_count += 1
        print(f"PASS YAML parse: {path}")


print()
print(f"Parsed Python guards : {python_count}")
print(f"Parsed YAML files    : {yaml_count}")
PY


# -----------------------------------------------------------------------------
# Ruff
#
# Unlike AST parsing, Ruff performs static Python linting.
#
# It currently covers:
#   - storage guards
#   - CI test code
#   - future tracked Python utilities
# -----------------------------------------------------------------------------

section "PYTHON LINT - RUFF"

mapfile -d '' PYTHON_FILES < <(
    git ls-files -z '*.py'
)

if (( ${#PYTHON_FILES[@]} == 0 )); then
    echo "No tracked Python files found."
else
    echo "Python files: ${#PYTHON_FILES[@]}"
    "$RUFF" check "${PYTHON_FILES[@]}"
fi


# -----------------------------------------------------------------------------
# yamllint
#
# PyYAML above answers:
#   "Can this YAML be parsed?"
#
# yamllint additionally answers:
#   "Does this YAML contain obvious style/formatting problems?"
#
# We start with the relaxed policy to obtain useful checks without turning
# formatting preferences into unnecessary pipeline blockers.
# -----------------------------------------------------------------------------

section "YAML LINT"

mapfile -d '' YAML_FILES < <(
    git ls-files -z '*.yml' '*.yaml'
)

if (( ${#YAML_FILES[@]} == 0 )); then
    echo "No tracked YAML files found."
else
    echo "YAML files: ${#YAML_FILES[@]}"

    # Flux's gotk-components.yaml is generated by `flux install --export`.
    # It contains upstream CRD/OpenAPI schema text whose formatting is not
    # repository-owned. The earlier PyYAML stage still parses it for syntax.
    #
    # Keep this exemption exact so all repository-authored YAML remains subject
    # to the normal yamllint policy.
    YAMLLINT_FILES=()

    for yaml_file in "${YAML_FILES[@]}"; do
        if [[ "$yaml_file" == "clusters/home-pi/flux-system/gotk-components.yaml" ]]; then
            echo "SKIP yamllint generated Flux manifest: $yaml_file"
            continue
        fi

        YAMLLINT_FILES+=("$yaml_file")
    done

    if (( ${#YAMLLINT_FILES[@]} == 0 )); then
        echo "No repository-owned YAML files require yamllint."
    else
        "$YAMLLINT" \
            -c .yamllint.yml \
            "${YAMLLINT_FILES[@]}"
    fi
fi


# -----------------------------------------------------------------------------
# actionlint
#
# GitHub workflow YAML can be valid YAML while still containing invalid:
#   - GitHub Actions expressions
#   - job relationships
#   - step syntax
#   - workflow-specific configuration
#
# Therefore GitHub workflows receive semantic validation from actionlint.
#
# Important:
#   We deliberately do NOT run actionlint against .gitea/workflows.
#   Gitea Actions is compatible with much of GitHub Actions syntax, but it is
#   not identical. Generic YAML validation still covers the Gitea workflow.
# -----------------------------------------------------------------------------

section "GITHUB ACTIONS LINT"

mapfile -d '' GITHUB_WORKFLOWS < <(
    git ls-files -z \
        '.github/workflows/*.yml' \
        '.github/workflows/*.yaml'
)

if (( ${#GITHUB_WORKFLOWS[@]} == 0 )); then
    echo "No GitHub Actions workflows found."
else
    echo "GitHub workflows: ${#GITHUB_WORKFLOWS[@]}"
    "$ACTIONLINT" "${GITHUB_WORKFLOWS[@]}"
fi


# -----------------------------------------------------------------------------
# Compose safety contract tests
#
# These are repository-specific regression tests, not generic Compose syntax.
#
# They protect architectural decisions such as:
#   - systemd owns startup instead of Docker restart policy
#   - persistent state uses explicit bind mounts
#   - create_host_path remains false
#   - externally reachable services bind explicitly
#   - the Gitea runner receives no host Docker socket
# -----------------------------------------------------------------------------

section "COMPOSE SAFETY CONTRACT TESTS"

"$PYTHON" -m unittest discover \
    -s scripts/ci/tests \
    -p 'test_*.py' \
    -v


# -----------------------------------------------------------------------------
# Ansible syntax validation
#
# Validate every tracked playbook independently.
#
# This verifies Ansible syntax but does NOT prove:
#   - runtime idempotence
#   - correct host state
#   - physical mount availability
#   - successful service readiness
# -----------------------------------------------------------------------------

section "ANSIBLE PLAYBOOK SYNTAX"

mapfile -d '' ANSIBLE_PLAYBOOKS < <(
    git ls-files -z 'ansible/playbooks/*.yml'
)

if (( ${#ANSIBLE_PLAYBOOKS[@]} == 0 )); then
    die "No tracked Ansible playbooks found."
fi

echo "Playbooks: ${#ANSIBLE_PLAYBOOKS[@]}"

for playbook in "${ANSIBLE_PLAYBOOKS[@]}"; do
    echo
    echo "--- Checking: $playbook ---"

    "$ANSIBLE" \
        --syntax-check \
        "$playbook"
done


# -----------------------------------------------------------------------------
# Docker Compose rendering
#
# Compose files reference environment-specific settings that are intentionally
# NOT committed to Git.
#
# CI therefore provides synthetic values purely to prove that each Compose
# project can be rendered successfully.
#
# Never put real passwords/tokens/secrets into this section.
# -----------------------------------------------------------------------------

section "COMPOSE CONFIGURATION"

if docker compose version >/dev/null 2>&1; then
    COMPOSE=(docker compose)
    echo "Compose implementation: docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE=(docker-compose)
    echo "Compose implementation: docker-compose"
else
    die "Docker Compose is unavailable."
fi


# ---------------------------------------------------------------------------
# Synthetic CI-only values.
#
# These exist solely so Compose interpolation can complete.
# ---------------------------------------------------------------------------

export STATE_SERVICES_ROOT=/srv/storage/state/services

export GITEA_FQDN=gitea.lab.home.arpa
export GITEA_BIND_IP=127.0.0.1

export GOTIFY_BIND_IP=127.0.0.1
export GOTIFY_ADMIN_INITIAL_PASSWORD=ci-placeholder-not-real

export UPTIME_KUMA_BIND_IP=127.0.0.1

export ACNG_BIND_IP=127.0.0.1
export ACNG_PUID=1000
export ACNG_PGID=1000


mapfile -d '' COMPOSE_MANIFESTS < <(
    git ls-files -z 'compose/*/compose.yml'
)

if (( ${#COMPOSE_MANIFESTS[@]} == 0 )); then
    die "No tracked Compose manifests found."
fi

echo "Compose manifests: ${#COMPOSE_MANIFESTS[@]}"

for manifest in "${COMPOSE_MANIFESTS[@]}"; do
    echo
    echo "--- Rendering: $manifest ---"

    "${COMPOSE[@]}" \
        --env-file /dev/null \
        -f "$manifest" \
        config --quiet
done


# -----------------------------------------------------------------------------
# Final result
# -----------------------------------------------------------------------------

section "VALIDATION COMPLETE"

echo "PASS: All platform validation checks completed."
echo "Git HEAD: $(git rev-parse --short HEAD)"
