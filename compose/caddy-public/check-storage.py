#!/usr/bin/env python3
"""Guard controller tunnel state, credential permissions and proxy isolation."""

import ipaddress
import json
import shutil
import stat
import subprocess
from pathlib import Path

MOUNT = Path("/srv/storage/state")
STATE = MOUNT / "services/caddy-public"
SECRET_DIR = MOUNT / "services/cloudflared"
TOKEN = SECRET_DIR / "tunnel-token"
COMPOSE = Path("/srv/platform/compose/caddy-public")
LABEL = "storage_sdcard"
ZULIP = MOUNT / "services/zulip"
ZULIP_COMPOSE = Path("/srv/platform/compose/zulip/compose.yaml")
ZULIP_SERVICES = {"zulip", "database", "memcached", "rabbitmq", "redis"}
ZULIP_SECRETS = {"postgres_password", "memcached_password", "rabbitmq_password",
                 "redis_password", "secret_key", "email_password"}


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
    colocated = set(services) == {"server", "cloudflared"} | ZULIP_SERVICES
    if set(services) != {"server", "cloudflared"} and not colocated:
        fail("Unexpected public ingress services")
    for service in services.values():
        if service.get("ports") or service.get("network_mode"):
            fail("Tunnel profile must not publish host ports or use host networking")
    required_networks = {"tunnel", "backend_egress", "edge_egress"}
    if colocated:
        required_networks |= {"zulip_proxy", "zulip_backend", "zulip_egress"}
    if set(project.get("networks", {})) != required_networks:
        fail("Unexpected public ingress networks")
    if any(network.get("external") for network in project["networks"].values()):
        fail("Public ingress must not join external application networks")
    origin_networks = {"tunnel", "backend_egress"} | ({"zulip_proxy"} if colocated else set())
    if (set(services["server"]["networks"]) != origin_networks
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
    if colocated:
        validate_zulip(project, subnet)


def validate_zulip(project, tunnel_subnet):
    services = project["services"]
    proxy = project["networks"]["zulip_proxy"]
    try:
        subnet = ipaddress.IPv4Network(proxy["ipam"]["config"][0]["subnet"])
        peer = ipaddress.IPv4Address(services["server"]["networks"]["zulip_proxy"]["ipv4_address"])
        app = ipaddress.IPv4Address(services["zulip"]["networks"]["zulip_proxy"]["ipv4_address"])
        reserved = (subnet.network_address, subnet.broadcast_address, subnet.network_address + 1)
        if (not proxy.get("internal") or app == peer or any(ip not in subnet or ip in reserved for ip in (peer, app))
                or subnet.overlaps(tunnel_subnet)):
            fail("Zulip proxy requires a separate internal subnet and usable Caddy peer")
    except (KeyError, ValueError):
        fail("Zulip proxy settings are invalid")
    if not project["networks"]["zulip_backend"].get("internal"):
        fail("Zulip dependencies must remain on an internal network")
    expected_mounts = {
        "zulip": ("data", "/data"), "database": ("postgresql", "/var/lib/postgresql/data"),
        "rabbitmq": ("rabbitmq", "/var/lib/rabbitmq"), "redis": ("redis", "/data"),
    }
    for name in ZULIP_SERVICES:
        service = services[name]
        networks = {"zulip_backend", "zulip_proxy", "zulip_egress"} if name == "zulip" else {"zulip_backend"}
        if set(service["networks"]) != networks or service.get("restart") != "no" or service.get("privileged"):
            fail("Zulip service isolation or guarded lifecycle is invalid")
        mounts = service.get("volumes", [])
        if name not in expected_mounts:
            if mounts:
                fail("Unexpected Zulip dependency mount")
            continue
        folder, target = expected_mounts[name]
        if len(mounts) != 1:
            fail("Unexpected Zulip persistent mounts")
        mount = mounts[0]
        if (mount.get("type") != "bind" or mount.get("source") != str(ZULIP / folder)
                or mount.get("target") != target or mount.get("read_only", False)
                or mount.get("bind", {}).get("create_host_path", True) is not False):
            fail("Zulip persistence violates the SD storage contract")
    for name in ZULIP_SECRETS:
        if project.get("secrets", {}).get("zulip__" + name, {}).get("file") != str(ZULIP / "secrets" / name):
            fail("Zulip secrets must use the canonical SD directory")
    environment = services["zulip"]["environment"]
    if environment.get("LOADBALANCER_IPS") != str(peer) or environment.get("TRUST_GATEWAY_IP") != "False":
        fail("Zulip must trust only the exact Caddy peer")
    if services["server"]["environment"].get("ZULIP_UPSTREAM") != "http://zulip:80":
        fail("Colocated Zulip must use its unpublished Docker upstream")
    if (environment.get("CONFIG_application_server__queue_workers_multiprocess") != "False"
            or environment.get("SETTING_OPEN_REALM_CREATION") != "False"):
        fail("Zulip requires threaded workers and closed organization creation")
    if environment.get("SETTING_EXTERNAL_HOST") != services["server"]["environment"].get("ZULIP_FQDN"):
        fail("Zulip and Caddy must use the same public hostname")


def validate_zulip_secrets(folder=ZULIP / "secrets"):
    info = folder.stat()
    if folder.is_symlink() or folder.resolve() != folder or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o700:
        fail("Zulip credential directory requires root ownership and mode 0700")
    for name in ZULIP_SECRETS:
        path = folder / name
        info = path.stat()
        if (path.is_symlink() or not stat.S_ISREG(info.st_mode) or info.st_uid != 0
                or stat.S_IMODE(info.st_mode) != 0o444):
            fail("Zulip file secrets require root ownership, mode 0444 and no redirects")
        value = path.read_bytes()
        if not value or len(value) > 16384 or any(c in value for c in (b"\n", b"\r", b"\x00")):
            fail("Zulip credential is missing or not single-line")


def validate_capacity(memory, free_state):
    # These are startup headroom checks for a small colocated deployment.
    # They are not an assurance that every workload will fit a 4 GB controller.
    if memory.get("MemTotal", 0) < 3 * 1024**2 or memory.get("SwapTotal", 0) < 1024**2:
        fail("Colocated Zulip needs at least 3 GiB host RAM and 1 GiB configured swap")
    if memory.get("MemAvailable", 0) < 1536 * 1024:
        fail("Insufficient startup memory headroom for colocated Zulip (1.5 GiB required)")
    if free_state < 10 * 1024**3:
        fail("Zulip requires at least 10 GiB free on SD state storage")


def main():
    if run(["/usr/bin/ls", "-A", str(MOUNT)]).returncode:
        fail("SD storage is inaccessible")
    mounted = run([
        "/usr/bin/findmnt", "--kernel", "--mountpoint", str(MOUNT),
        "--types", "ext4", "--noheadings", "--output", "LABEL",
    ])
    if mounted.returncode or mounted.stdout.strip() != LABEL:
        fail("Expected ext4 SD filesystem is not mounted")
    for path in (STATE, STATE / "data", STATE / "config", SECRET_DIR, ZULIP,
                 *(ZULIP / name for name in ("data", "postgresql", "rabbitmq", "redis", "secrets"))):
        if not path.is_dir() or path.is_symlink() or path.resolve() != path:
            fail("Public ingress state is missing or redirected")
        backing = run([
            "/usr/bin/findmnt", "--kernel", "--target", str(path),
            "--types", "ext4", "--noheadings", "--output", "TARGET,LABEL",
        ])
        if backing.returncode or backing.stdout.split() != [str(MOUNT), LABEL]:
            fail("Public ingress state is not on the expected SD mount")
    validate_secret()
    try:
        validate_zulip_secrets()
    except OSError:
        fail("Zulip secrets are unavailable; run zulip-init-secrets")
    command = [
        "/usr/bin/docker-compose", "--env-file", str(COMPOSE / ".env"),
        "-f", str(COMPOSE / "compose.yaml"), "-f", str(ZULIP_COMPOSE),
    ]
    rendered = run([*command, "config", "--format", "json"])
    if rendered.returncode:
        fail("Compose configuration could not be rendered")
    project = json.loads(rendered.stdout)
    if set(project["services"]) != {"server", "cloudflared"} | ZULIP_SERVICES:
        fail("The controller lifecycle requires both ingress and Zulip manifests")
    validate_project(project)
    running = run([*command, "ps", "--status", "running", "--quiet", "zulip"])
    if running.returncode:
        fail("Could not inspect the existing Zulip runtime")
    if not running.stdout.strip():
        memory = {line.split()[0].rstrip(":"): int(line.split()[1])
                  for line in Path("/proc/meminfo").read_text().splitlines() if len(line.split()) >= 2}
        validate_capacity(memory, shutil.disk_usage(ZULIP).free)
    print("Public ingress preflight PASSED. No credential value was printed.")


if __name__ == "__main__":
    main()
