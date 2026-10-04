#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== CI DEPENDENCY BOOTSTRAP ==="

if [[ ! -x .ci-venv/bin/ansible-playbook ]]; then
    python3 -m venv .ci-venv

    .ci-venv/bin/python -m pip install \
        --disable-pip-version-check \
        'ansible-core==2.19.11' \
        'PyYAML>=6,<7'
fi

# Hosted CI requires ShellCheck. Local users may install it
# independently without making host bootstrap depend on CI.
if [[ "${CI:-false}" == "true" ]] &&
   ! command -v shellcheck >/dev/null 2>&1; then

    sudo apt-get update -qq
    sudo apt-get install -y -qq shellcheck
fi

echo "CI dependencies ready."
