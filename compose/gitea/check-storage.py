#!/usr/bin/env python3
"""Fail closed unless Gitea uses the expected mounted SD filesystem."""

import json
import subprocess
from pathlib import Path

MOUNT = Path("/srv/storage/state")
DATA = MOUNT / "services/gitea"
COMPOSE_DIR = Path("/srv/platform/compose/gitea")
EXPECTED_LABEL = "storage_sdcard"


def fail(message):
    raise SystemExit(f"Gitea storage preflight FAILED: {message}")


# Access the directory to trigger systemd's SD automount.
activation = subprocess.run(
    ["/usr/bin/ls", "-A", str(MOUNT)],
    capture_output=True,
    text=True,
    check=False,
)

if activation.returncode != 0:
    fail("SD storage directory is inaccessible")


# Directory existence is insufficient: verify the actual ext4 mount.
mount = subprocess.run(
    [
        "/usr/bin/findmnt",
        "--kernel",
        "--mountpoint", str(MOUNT),
        "--types", "ext4",
        "--noheadings",
        "--output", "LABEL",
    ],
    capture_output=True,
    text=True,
    check=False,
)

if mount.returncode != 0 or mount.stdout.strip() != EXPECTED_LABEL:
    fail("Expected storage_sdcard ext4 filesystem is not mounted")


if not DATA.is_dir():
    fail("Ansible-managed Gitea data directory is missing")


# Reject symlinks that might redirect application writes elsewhere.
if DATA.resolve() != DATA:
    fail("Gitea storage path resolves outside its declared location")


# Verify that the data directory is actually on the expected mount.
backing = subprocess.run(
    [
        "/usr/bin/findmnt",
        "--kernel",
        "--target", str(DATA),
        "--types", "ext4",
        "--noheadings",
        "--output", "TARGET,LABEL",
    ],
    capture_output=True,
    text=True,
    check=False,
)

if backing.returncode != 0 or backing.stdout.split() != [
    str(MOUNT), EXPECTED_LABEL
]:
    fail("Gitea data is not backed by the expected SD mount")


# Check the fully interpolated Compose configuration, not just .env.
rendered = subprocess.run(
    [
        "/usr/bin/docker-compose",
        "--env-file", str(COMPOSE_DIR / ".env"),
        "-f", str(COMPOSE_DIR / "compose.yml"),
        "config", "--format", "json",
    ],
    capture_output=True,
    text=True,
    check=False,
)

if rendered.returncode != 0:
    fail("Compose configuration could not be rendered")

config = json.loads(rendered.stdout)

data_volumes = [
    volume
    for volume in config["services"]["server"]["volumes"]
    if volume.get("target") == "/data"
]

if (
    len(data_volumes) != 1
    or data_volumes[0].get("type") != "bind"
    or data_volumes[0].get("source") != str(DATA)
):
    fail("Compose /data binding violates the storage contract")


print("Gitea storage preflight PASSED.")
