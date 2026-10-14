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
AUTH = MOUNT / "services/prometheus-auth"
AUTH_GID = 29012

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

# Scoped runtime observer copy only; never mount the deployer identity.
if AUTH.is_symlink() or not AUTH.is_dir() or AUTH.resolve() != AUTH:
    fail("Missing or unsafe observer runtime directory")
info = AUTH.stat()
if (info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode)) != (0, AUTH_GID, 0o750):
    fail("Unsafe observer runtime directory ownership or permissions")
backing = run([
    "/usr/bin/findmnt", "--kernel", "--target", str(AUTH),
    "--types", "ext4", "--noheadings", "--output", "TARGET,LABEL",
])
if backing.split() != [str(MOUNT), LABEL]:
    fail("Observer credentials not on expected SD filesystem")
for filename in ("client.key", "client.crt", "ca.crt"):
    item = AUTH / filename
    if item.is_symlink() or not item.is_file():
        fail(f"Missing or symlinked observer {filename}")
    info = item.stat()
    if (info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode)) != (0, AUTH_GID, 0o640):
        fail(f"Unsafe observer {filename} permissions")
cert, key, ca = (AUTH / name for name in ("client.crt", "client.key", "ca.crt"))
run(["/usr/bin/openssl", "verify", "-purpose", "sslclient",
     "-CAfile", str(ca), str(cert)])
run(["/usr/bin/openssl", "x509", "-in", str(cert), "-checkend", "86400", "-noout"])
subject = run(["/usr/bin/openssl", "x509", "-in", str(cert),
               "-noout", "-subject", "-nameopt", "RFC2253"])
if subject != "subject=CN=platform-observer":
    fail("Wrong observer identity")
usage = run(["/usr/bin/openssl", "x509", "-in", str(cert),
             "-noout", "-ext", "extendedKeyUsage"])
if not any(tag in usage for tag in (
    "TLS Web Client Authentication", "clientAuth", "1.3.6.1.5.5.7.3.2",
)):
    fail("Missing observer clientAuth EKU")
key_pub = run(["/usr/bin/openssl", "pkey", "-in", str(key), "-pubout"])
cert_pub = run(["/usr/bin/openssl", "x509", "-in", str(cert), "-pubkey", "-noout"])
if key_pub != cert_pub:
    fail("Observer key and certificate do not match")

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

if service.get("group_add") != [str(AUTH_GID)]:
    fail("Unexpected Prometheus supplemental groups")
volumes = service.get("volumes", [])
if len(volumes) != 3 or len({v.get("target") for v in volumes}) != 3:
    fail("Unexpected Prometheus mount count or duplicate target")

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

observer_mount = [v for v in volumes if v.get("target") == "/run/secrets/platform-observer"]
if (
    len(observer_mount) != 1
    or observer_mount[0].get("source") != str(AUTH)
    or observer_mount[0].get("type") != "bind"
    or observer_mount[0].get("read_only") is not True
    or observer_mount[0].get("bind", {}).get("create_host_path", False) is not False
):
    fail("Unsafe observer credential bind mount")

# Compose can erase explicit false values when rendering JSON.
# Enforce the original, exact long-form mount declaration too.
# Keep this deliberately strict: changes in source shape must be
# reviewed rather than silently relaxing the no-create invariant.
source_text = COMPOSE.read_text(encoding="utf-8")
marker = "\n  prometheus:\n"
required = (
    "      - type: bind\n"
    "        source: ${STATE_SERVICES_ROOT:?Set STATE_SERVICES_ROOT}/prometheus-auth\n"
    "        target: /run/secrets/platform-observer\n"
    "        read_only: true\n"
    "        bind:\n"
    "          create_host_path: false\n"
)

if source_text.count(marker) != 1:
    fail("Cannot locate unique Prometheus source declaration")

prometheus_source = source_text.split(marker, 1)[1]

if prometheus_source.count(required) != 1:
    fail("Observer source must explicitly prohibit host-path creation")

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
