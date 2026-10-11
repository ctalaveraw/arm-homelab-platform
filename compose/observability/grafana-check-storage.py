#!/usr/bin/env python3
"""Fail closed unless Grafana uses the approved SD and Compose contract."""

import json
import os
import stat
import subprocess
from pathlib import Path

MOUNT = Path("/srv/storage/state")
ROOT = MOUNT / "services"
DATA = ROOT / "grafana"
AUTH = ROOT / "grafana-auth"
SECRET = AUTH / "admin-password"
COMPOSE = Path("/srv/platform/compose/observability/compose.yml")
SOURCE = COMPOSE.parent / "grafana"

DISABLED_PLUGINS = {
    "elasticsearch",
    "grafana-postgresql-datasource",
    "grafana-pyroscope-datasource",
    "influxdb",
    "jaeger",
    "loki",
    "mssql",
    "mysql",
    "opentsdb",
    "stackdriver",
    "tempo",
    "zipkin",
}


def fail(message):
    raise SystemExit(f"Grafana storage preflight FAILED: {message}")


def run(argv, *, env=None):
    result = subprocess.run(
        argv, capture_output=True, text=True, check=False, env=env
    )
    if result.returncode:
        fail(f"Command failed: {argv[0]}")
    return result.stdout.strip()


run(["/usr/bin/ls", "-A", str(MOUNT)])

label = run([
    "/usr/bin/findmnt", "--kernel", "--mountpoint", str(MOUNT),
    "--types", "ext4", "--noheadings", "--output", "LABEL",
])
if label != "storage_sdcard":
    fail("Expected labeled ext4 SD filesystem is not mounted")

for directory, uid, gid, mode in (
    (DATA, 472, 472, 0o750),
    (AUTH, 0, 0, 0o700),
):
    if directory.is_symlink() or not directory.is_dir():
        fail(f"Missing or unsafe directory: {directory}")
    if directory.resolve() != directory:
        fail(f"Symlink in directory path: {directory}")
    info = directory.stat()
    if (info.st_uid, info.st_gid) != (uid, gid):
        fail(f"Unexpected directory owner: {directory}")
    if stat.S_IMODE(info.st_mode) != mode:
        fail(f"Unexpected directory permissions: {directory}")
    backing = run([
        "/usr/bin/findmnt", "--kernel", "--target", str(directory),
        "--types", "ext4", "--noheadings", "--output", "TARGET,LABEL",
    ])
    if backing.split() != [str(MOUNT), "storage_sdcard"]:
        fail(f"Directory is not SD-backed: {directory}")

if SECRET.is_symlink() or not SECRET.is_file():
    fail("Admin secret is missing or is a symlink")

info = SECRET.stat()
if (
    (info.st_uid, info.st_gid) != (472, 472)
    or stat.S_IMODE(info.st_mode) != 0o400
    or info.st_size < 32
):
    fail("Admin secret ownership, permissions or length is unsafe")

for filename in (
    SOURCE / "provisioning/datasources/prometheus.yml",
    SOURCE / "provisioning/dashboards/platform.yml",
    SOURCE / "dashboards/platform-overview.json",
):
    if filename.is_symlink() or not filename.is_file():
        fail(f"Missing or unsafe provisioning file: {filename}")
    if stat.S_IMODE(filename.stat().st_mode) != 0o644:
        fail(f"Unreadable provisioning file mode: {filename}")

environment = {
    **os.environ,
    "STATE_SERVICES_ROOT": str(ROOT),
}
rendered = run([
    "/usr/bin/docker-compose", "--env-file", "/dev/null",
    "-f", str(COMPOSE), "config", "--format", "json",
], env=environment)

try:
    service = json.loads(rendered)["services"]["grafana"]
except (ValueError, TypeError, KeyError) as exc:
    fail(f"Invalid Compose configuration: {exc}")

expected = {
    "/var/lib/grafana": (DATA, False),
    "/run/secrets/grafana-admin-password": (SECRET, True),
    "/etc/grafana/provisioning": (SOURCE / "provisioning", True),
    "/etc/grafana/dashboards": (SOURCE / "dashboards", True),
}

volumes = service.get("volumes", [])
if len(volumes) != len(expected):
    fail("Unexpected Grafana volume count")

found = set()
for volume in volumes:
    target = volume.get("target")
    if target in found or target not in expected:
        fail("Unexpected or duplicate Grafana mount")
    found.add(target)
    source, readonly = expected[target]
    if (
        volume.get("type") != "bind"
        or volume.get("source") != str(source)
        or volume.get("read_only", False) is not readonly
    ):
        fail(f"Unsafe Grafana mount: {target}")

ports = service.get("ports", [])
if (
    len(ports) != 1
    or ports[0].get("host_ip") != "10.0.0.50"
    or str(ports[0].get("published")) != "3300"
    or ports[0].get("target") != 3000
):
    fail("Grafana must publish only localhost port 3300")

env = service.get("environment", {})
if (
    env.get("GF_SECURITY_ADMIN_PASSWORD__FILE")
    != "/run/secrets/grafana-admin-password"
    or "GF_SECURITY_ADMIN_PASSWORD" in env
    or env.get("GF_PLUGINS_PREINSTALL_AUTO_UPDATE") != "false"
):
    fail("Unsafe Grafana credentials or plugin-update configuration")


disabled = {
    item.strip()
    for item in env.get("GF_PLUGINS_DISABLE_PLUGINS", "").split(",")
    if item.strip()
}

if disabled != DISABLED_PLUGINS:
    fail("Unexpected Grafana plugin loading policy")

if (
    service.get("restart") != "no"
    or service.get("user") != "472:472"
    or service.get("read_only") is not True
    or service.get("privileged") is True
    or service.get("network_mode") == "host"
    or service.get("cap_drop") != ["ALL"]
    or "no-new-privileges:true" not in service.get("security_opt", [])
    or int(service.get("mem_limit", 0)) != 805306368
    or service.get("pids_limit") != 256
):
    fail("Unsafe Grafana runtime security contract")

print("PASS: Grafana guarded storage, credentials and Compose configuration")
