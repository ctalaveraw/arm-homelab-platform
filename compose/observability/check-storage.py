#!/usr/bin/env python3
"""Reject unsafe Prometheus storage or Compose configuration."""

import json
import os
import stat
import subprocess
from pathlib import Path

MOUNT = Path("/srv/storage/state")
DATA = MOUNT / "services/prometheus"
COMPOSE = Path("/srv/platform/compose/observability/compose.yml")
CONFIG = COMPOSE.with_name("prometheus.yml")

LABEL = "storage_sdcard"
UID = 65534
GID = 65534


def fail(message):
    raise SystemExit(f"Prometheus storage preflight FAILED: {message}")


def run(argv, *, env=None):
    result = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        fail(f"Command failed: {argv[0]}")
    return result.stdout.strip()


# Trigger the SD automount before checking the backing filesystem.
run(["/usr/bin/ls", "-A", str(MOUNT)])

mounted_label = run([
    "/usr/bin/findmnt",
    "--kernel",
    "--mountpoint", str(MOUNT),
    "--types", "ext4",
    "--noheadings",
    "--output", "LABEL",
])

if mounted_label != LABEL:
    fail("Expected labeled ext4 SD filesystem is not mounted")

if not DATA.is_dir():
    fail("Ansible-managed persistent directory is missing")

if DATA.resolve() != DATA:
    fail("Persistent directory contains an unsafe symlink")

backing = run([
    "/usr/bin/findmnt",
    "--kernel",
    "--target", str(DATA),
    "--types", "ext4",
    "--noheadings",
    "--output", "TARGET,LABEL",
])

if backing.split() != [str(MOUNT), LABEL]:
    fail("Persistent directory is not backed by the expected SD mount")

if CONFIG.is_symlink() or not CONFIG.is_file():
    fail("Prometheus configuration must be a regular file")

if stat.S_IMODE(CONFIG.stat().st_mode) != 0o644:
    fail("Prometheus configuration must have mode 0644")

metadata = DATA.stat()

if (metadata.st_uid, metadata.st_gid) != (UID, GID):
    fail("Unexpected persistent directory ownership")

if stat.S_IMODE(metadata.st_mode) != 0o750:
    fail("Unexpected persistent directory permissions")

environment = {
    **os.environ,
    "STATE_SERVICES_ROOT": str(MOUNT / "services"),
}

rendered = run([
    "/usr/bin/docker-compose",
    "--env-file", "/dev/null",
    "-f", str(COMPOSE),
    "config", "--format", "json",
], env=environment)

try:
    service = json.loads(rendered)["services"]["prometheus"]
except (ValueError, KeyError, TypeError) as exc:
    fail(f"Invalid rendered Compose service: {exc}")

volumes = service.get("volumes", [])

data_bindings = [
    item for item in volumes
    if item.get("target") == "/prometheus"
]

if (
    len(data_bindings) != 1
    or data_bindings[0].get("type") != "bind"
    or data_bindings[0].get("source") != str(DATA)
):
    fail("Rendered Prometheus state binding is unsafe")

config_bindings = [
    item for item in volumes
    if item.get("target") == "/etc/prometheus/prometheus.yml"
]

if (
    len(config_bindings) != 1
    or config_bindings[0].get("type") != "bind"
    or config_bindings[0].get("source") != str(CONFIG)
    or config_bindings[0].get("read_only") is not True
):
    fail("Rendered Prometheus configuration binding is unsafe")

ports = service.get("ports", [])

if (
    len(ports) != 1
    or ports[0].get("host_ip") != "127.0.0.1"
    or str(ports[0].get("published")) != "9090"
    or ports[0].get("target") != 9090
):
    fail("Prometheus must publish only localhost port 9090")

if service.get("restart") != "no":
    fail("Docker restart policy must not bypass systemd")

print("PASS: Prometheus guarded storage and Compose configuration")
