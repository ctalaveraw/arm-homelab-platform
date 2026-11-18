#!/usr/bin/env python3
"""Guard controller tunnel state, credential permissions and proxy isolation."""

import ipaddress
import json
import stat
import subprocess
from pathlib import Path

MOUNT = Path("/srv/storage/state")
STATE = MOUNT / "services/caddy-public"
SECRET_DIR = MOUNT / "services/cloudflared"
TOKEN = SECRET_DIR / "tunnel-token"
COMPOSE = Path("/srv/platform/compose/caddy-public")
LABEL = "storage_sdcard"


def fail(message):
    raise SystemExit(f"Public ingress preflight FAILED: {message}")


def run(argv):
    return subprocess.run(argv, capture_output=True, text=True, check=False)


def validate_secret(path=TOKEN):
    if path.is_symlink() or path.resolve() != path:
        fail("Tunnel token storage is redirected")
    try:
        info = path.stat()
        parent = path.parent.stat()
        if not stat.S_ISREG(info.st_mode):
            fail("Tunnel token must be a regular file")
        if (info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode)) != (0, 65532, 0o440):
            fail("Tunnel token requires owner root, group 65532 and mode 0440")
        if parent.st_uid != 0 or stat.S_IMODE(parent.st_mode) != 0o700:
            fail("Tunnel credential directory requires root ownership and mode 0700")
        value = path.read_bytes()
        if not value or len(value) > 16384 or any(c in value for c in (b"\n", b"\r", b"\x00")):
            fail("Tunnel token is empty or not single-line")
    except OSError:
        fail("Tunnel token is unavailable; use the hidden-input installer")


def validate_project(project):
    services = project["services"]
    if set(services) != {"server", "cloudflared"}:
        fail("Unexpected public ingress services")
    for service in services.values():
        if service.get("ports") or service.get("network_mode"):
            fail("Tunnel profile must not publish host ports or use host networking")
    required_networks = {"tunnel", "backend_egress", "edge_egress"}
    if set(project.get("networks", {})) != required_networks:
        fail("Unexpected public ingress networks")
    if any(network.get("external") for network in project["networks"].values()):
        fail("Public ingress must not join external application networks")
    if (set(services["server"]["networks"]) != {"tunnel", "backend_egress"}
            or set(services["cloudflared"]["networks"]) != {"tunnel", "edge_egress"}):
        fail("Tunnel connector and origin must share only their private proxy network")
    volumes = services["server"].get("volumes", [])
    expected = {
        "/data": (str(STATE / "data"), False),
        "/config": (str(STATE / "config"), False),
        "/etc/caddy/Caddyfile": (str(COMPOSE / "Caddyfile"), True),
    }
    if len(volumes) != len(expected) or {v.get("target") for v in volumes} != set(expected):
        fail("Unexpected persistent mounts")
    for volume in volumes:
        source, readonly = expected.get(volume.get("target"), (None, None))
        if (volume.get("source") != source or volume.get("type") != "bind"
                or volume.get("read_only", False) != readonly
                or volume.get("bind", {}).get("create_host_path", True) is not False):
            fail("Compose persistence violates the SD storage contract")
    connector = services["cloudflared"]
    if connector.get("volumes") or connector.get("user") != "65532:65532":
        fail("Tunnel connector must use its nonroot identity and file secret only")
    if project.get("secrets", {}).get("tunnel_token", {}).get("file") != str(TOKEN):
        fail("Tunnel token must come from the canonical SD credential file")
    if "--token-file" not in connector.get("command", []) or "--token" in connector.get("command", []):
        fail("Tunnel credentials must not be supplied as command arguments")
    if any(key in connector.get("environment", {}) for key in ("TUNNEL_TOKEN", "CLOUDFLARE_API_TOKEN")):
        fail("Tunnel credentials must not be supplied in the environment")
    try:
        network = project["networks"]["tunnel"]
        subnet = ipaddress.IPv4Network(network["ipam"]["config"][0]["subnet"])
        origin = ipaddress.IPv4Address(services["server"]["networks"]["tunnel"]["ipv4_address"])
        peer = ipaddress.IPv4Address(connector["networks"]["tunnel"]["ipv4_address"])
        reserved = (subnet.network_address, subnet.broadcast_address, subnet.network_address + 1)
        if not network.get("internal") or origin == peer or any(ip not in subnet or ip in reserved for ip in (origin, peer)):
            fail("Tunnel proxy addresses must be distinct usable hosts on an internal network")
        if services["server"]["environment"].get("CLOUDFLARED_CONTAINER_IP") != str(peer):
            fail("Caddy must trust the exact tunnel connector address")
    except (KeyError, ValueError):
        fail("Tunnel proxy network settings are invalid")


def main():
    if run(["/usr/bin/ls", "-A", str(MOUNT)]).returncode:
        fail("SD storage is inaccessible")
    mounted = run([
        "/usr/bin/findmnt", "--kernel", "--mountpoint", str(MOUNT),
        "--types", "ext4", "--noheadings", "--output", "LABEL",
    ])
    if mounted.returncode or mounted.stdout.strip() != LABEL:
        fail("Expected ext4 SD filesystem is not mounted")
    for path in (STATE, STATE / "data", STATE / "config", SECRET_DIR):
        if not path.is_dir() or path.is_symlink() or path.resolve() != path:
            fail("Public ingress state is missing or redirected")
        backing = run([
            "/usr/bin/findmnt", "--kernel", "--target", str(path),
            "--types", "ext4", "--noheadings", "--output", "TARGET,LABEL",
        ])
        if backing.returncode or backing.stdout.split() != [str(MOUNT), LABEL]:
            fail("Public ingress state is not on the expected SD mount")
    validate_secret()
    rendered = run([
        "/usr/bin/docker-compose", "--env-file", str(COMPOSE / ".env"),
        "-f", str(COMPOSE / "compose.yaml"), "config", "--format", "json",
    ])
    if rendered.returncode:
        fail("Compose configuration could not be rendered")
    validate_project(json.loads(rendered.stdout))
    print("Public ingress preflight PASSED. No credential value was printed.")


if __name__ == "__main__":
    main()
