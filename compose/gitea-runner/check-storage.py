#!/usr/bin/env python3
"""Fail closed unless the Gitea runner uses its registered SD-backed identity."""

import json
import stat
import subprocess
from pathlib import Path

MOUNT = Path("/srv/storage/state")
DATA = MOUNT / "services/gitea-runner"
IDENTITY = DATA / ".runner"
COMPOSE = Path("/srv/platform/compose/gitea-runner")
EXPECTED_LABEL = "storage_sdcard"


def fail(message):
    raise SystemExit(f"Gitea runner storage FAILED: {message}")


def run(argv):
    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        check=False,
    )


# Trigger systemd automount before checking the actual filesystem.
activation = run(["/usr/bin/ls", "-A", str(MOUNT)])
if activation.returncode != 0:
    fail("SD storage is inaccessible")

mount = run([
    "/usr/bin/findmnt",
    "--kernel", "--mountpoint", str(MOUNT),
    "--types", "ext4",
    "--noheadings", "--output", "LABEL",
])

if mount.returncode != 0 or mount.stdout.strip() != EXPECTED_LABEL:
    fail("Expected ext4 SD filesystem is not mounted")

if not DATA.is_dir() or DATA.is_symlink() or DATA.resolve() != DATA:
    fail("Persistent runner directory is missing or redirected")

backing = run([
    "/usr/bin/findmnt",
    "--kernel", "--target", str(DATA),
    "--types", "ext4",
    "--noheadings", "--output", "TARGET,LABEL",
])

if backing.returncode != 0 or backing.stdout.split() != [
    str(MOUNT), EXPECTED_LABEL
]:
    fail("Runner identity is not backed by the expected SD mount")

directory = DATA.stat()
if (
    directory.st_uid != 10001
    or directory.st_gid != 10001
    or stat.S_IMODE(directory.st_mode) != 0o700
):
    fail("Runner directory ownership or permissions are incorrect")

if IDENTITY.is_symlink() or not IDENTITY.is_file():
    fail("Registered runner identity is missing or redirected")

identity = IDENTITY.stat()
if (
    identity.st_uid != 10001
    or identity.st_gid != 10001
    or stat.S_IMODE(identity.st_mode) != 0o600
):
    fail("Runner identity ownership or permissions are incorrect")

rendered = run([
    "/usr/bin/docker-compose",
    "--env-file", str(COMPOSE / ".env"),
    "-f", str(COMPOSE / "compose.yml"),
    "config", "--format", "json",
])

if rendered.returncode != 0:
    fail("Compose configuration could not be rendered")

config = json.loads(rendered.stdout)
service = config["services"]["runner"]

volumes = service.get("volumes", [])

if (
    len(volumes) != 1
    or volumes[0].get("type") != "bind"
    or volumes[0].get("source") != str(DATA)
    or volumes[0].get("target") != "/data"
):
    fail("Runner Compose persistence violates the storage contract")

if service.get("privileged") or service.get("ports"):
    fail("Runner exposes unexpected host privileges or ports")

print("Gitea runner storage preflight PASSED.")
