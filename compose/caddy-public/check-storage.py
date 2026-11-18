#!/usr/bin/env python3
"""Validate Caddy's persistent certificate storage before container startup."""

import json
import subprocess
from pathlib import Path

MOUNT = Path("/srv/storage/state")
STATE = MOUNT / "services/caddy-public"
COMPOSE = Path("/srv/platform/compose/caddy-public")
LABEL = "storage_sdcard"


def fail(message):
    raise SystemExit(f"Caddy storage preflight FAILED: {message}")


def run(argv):
    return subprocess.run(argv, capture_output=True, text=True, check=False)


def main():
    if run(["/usr/bin/systemctl", "is-active", "--quiet", "caddy.service"]).returncode == 0:
        fail("Legacy Forgejo caddy.service owns the listener; resolve public/private routing first")

    if run(["/usr/bin/ls", "-A", str(MOUNT)]).returncode:
        fail("SD storage is inaccessible")

    mount = run([
        "/usr/bin/findmnt", "--kernel", "--mountpoint", str(MOUNT),
        "--types", "ext4", "--noheadings", "--output", "LABEL",
    ])
    if mount.returncode or mount.stdout.strip() != LABEL:
        fail("Expected ext4 SD filesystem is not mounted")

    for path in (STATE, STATE / "data", STATE / "config"):
        if not path.is_dir() or path.is_symlink() or path.resolve() != path:
            fail("Certificate storage is missing or redirected")
        backing = run([
            "/usr/bin/findmnt", "--kernel", "--target", str(path),
            "--types", "ext4", "--noheadings", "--output", "TARGET,LABEL",
        ])
        if backing.returncode or backing.stdout.split() != [str(MOUNT), LABEL]:
            fail("Certificate storage is not on the expected SD mount")

    rendered = run([
        "/usr/bin/docker-compose", "--env-file", str(COMPOSE / ".env"),
        "-f", str(COMPOSE / "compose.yaml"), "config", "--format", "json",
    ])
    if rendered.returncode:
        fail("Compose configuration could not be rendered")
    service = json.loads(rendered.stdout)["services"]["server"]
    volumes = service.get("volumes", [])
    expected = {
        "/data": (str(STATE / "data"), False),
        "/config": (str(STATE / "config"), False),
        "/etc/caddy/Caddyfile": (str(COMPOSE / "Caddyfile"), True),
    }
    if len(volumes) != len(expected) or {v.get("target") for v in volumes} != set(expected):
        fail("Unexpected persistent mounts")
    for volume in volumes:
        source, readonly = expected.get(volume.get("target"), (None, None))
        if (
            source is None or volume.get("source") != source
            or volume.get("type") != "bind"
            or volume.get("read_only", False) != readonly
            or volume.get("bind", {}).get("create_host_path", True) is not False
        ):
            fail("Compose persistence violates the certificate storage contract")
    print("Caddy storage preflight PASSED.")


if __name__ == "__main__":
    main()
