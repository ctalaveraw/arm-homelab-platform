#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== PLATFORM VALIDATION ==="
echo "Architecture: $(uname -m)"

if [[ -x .ci-venv/bin/python ]]; then
    PYTHON=.ci-venv/bin/python
    ANSIBLE=.ci-venv/bin/ansible-playbook
else
    PYTHON=python3
    ANSIBLE=ansible-playbook
fi

echo
echo "=== SHELL SYNTAX ==="
bash -n scripts/ci/*.sh

if command -v shellcheck >/dev/null 2>&1; then
    shellcheck scripts/ci/*.sh
elif [[ "${CI:-false}" == "true" ]]; then
    echo "FAIL: ShellCheck unavailable in CI."
    exit 1
else
    echo "WARN: Local ShellCheck unavailable; syntax check passed."
fi

echo
echo "=== PYTHON AND YAML VALIDATION ==="

"$PYTHON" <<'PY'
import ast
import subprocess
from pathlib import Path

import yaml

tracked = [
    Path(item)
    for item in subprocess.check_output(
        ["git", "ls-files", "--cached", "-z"]
    ).decode().split("\0")
    if item
]

for path in tracked:
    if path.name == "check-storage.py":
        ast.parse(path.read_text(), filename=str(path))
        print(f"PASS Python: {path}")

    if path.suffix in {".yml", ".yaml"}:
        with path.open() as stream:
            list(yaml.safe_load_all(stream))
        print(f"PASS YAML: {path}")
PY

echo
echo "=== COMPOSE SAFETY CONTRACT TESTS ==="

"$PYTHON" -m unittest discover \
    -s scripts/ci/tests \
    -p 'test_*.py' \
    -v

echo
echo "=== ANSIBLE PLAYBOOK SYNTAX ==="

while IFS= read -r -d '' playbook; do
    echo "Checking: $playbook"
    "$ANSIBLE" --syntax-check "$playbook"
done < <(git ls-files -z 'ansible/playbooks/*.yml')

echo
echo "=== COMPOSE CONFIGURATION ==="

if docker compose version >/dev/null 2>&1; then
    COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE=(docker-compose)
else
    echo "FAIL: Docker Compose is unavailable."
    exit 1
fi

# Synthetic values only. Never render or print real secrets.
export STATE_SERVICES_ROOT=/srv/storage/state/services
export GITEA_FQDN=gitea.lab.home.arpa
export GITEA_BIND_IP=127.0.0.1
export GOTIFY_BIND_IP=127.0.0.1
export GOTIFY_ADMIN_INITIAL_PASSWORD=ci-placeholder-not-real
export UPTIME_KUMA_BIND_IP=127.0.0.1
export ACNG_BIND_IP=127.0.0.1
export ACNG_PUID=1000
export ACNG_PGID=1000

while IFS= read -r -d '' manifest; do
    echo "Checking: $manifest"

    "${COMPOSE[@]}" \
        --env-file /dev/null \
        -f "$manifest" \
        config --quiet

done < <(git ls-files -z 'compose/*/compose.yml')

echo
echo "PASS: All platform validation checks completed."
