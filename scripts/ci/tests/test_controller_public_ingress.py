"""Guard public ingress isolation from the parallel private Forgejo profile."""

import importlib.util
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[3]
PROFILE = ROOT / "compose/caddy-public"
SPEC = importlib.util.spec_from_file_location(
    "public_guard", PROFILE / "check-storage.py"
)
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)


class PublicIngressTests(unittest.TestCase):
    def test_public_routes_exclude_forgejo(self):
        config = (PROFILE / "Caddyfile").read_text()
        self.assertEqual(config.count("reverse_proxy "), 1)
        self.assertIn("{$ZULIP_FQDN}", config)
        self.assertIn("{$ZULIP_UPSTREAM}", config)
        self.assertNotIn("forgejo", config.lower())
        self.assertNotIn("on_demand", config)
        self.assertIn("protocols h1 h2", config)

    def test_public_container_has_no_private_forge_network(self):
        config = yaml.safe_load((PROFILE / "compose.yaml").read_text())
        service = config["services"]["server"]
        self.assertNotIn("networks", config)
        self.assertNotIn("network_mode", service)
        self.assertNotIn("platform_ingress", str(config))
        self.assertNotIn("docker.sock", str(config))
        self.assertEqual(service["restart"], "no")
        self.assertEqual(service["cap_drop"], ["ALL"])
        self.assertEqual(service["read_only"], True)
        self.assertEqual(service["ports"], [
            "${PROXY_BIND_IP:?Set PROXY_BIND_IP}:80:80/tcp",
            "${PROXY_BIND_IP:?Set PROXY_BIND_IP}:443:443/tcp",
        ])

    def test_app_override_disables_collocated_caddy_and_limits_proxy_trust(self):
        config = yaml.safe_load(
            (PROFILE / "zulip-upstream.override.yaml").read_text()
        )["services"]
        self.assertEqual(config["caddy"]["profiles"], ["legacy-collocated-ingress"])
        self.assertEqual(config["zulip"]["ports"], [
            "${ZULIP_BIND_IPV4:?Set ZULIP_BIND_IPV4}:8080:80/tcp"
        ])
        self.assertEqual(config["zulip"]["environment"]["LOADBALANCER_IPS"],
                         "${CONTROLLER_PROXY_IPV4:?Set CONTROLLER_PROXY_IPV4}")
        self.assertEqual(config["zulip"]["environment"]["TRUST_GATEWAY_IP"], "False")

    def test_public_lifecycle_is_independent_of_forgejo(self):
        unit = (PROFILE / "caddy-public.service").read_text()
        self.assertNotIn("forgejo.service", unit)
        self.assertIn("caddy-public-check-storage", unit)
        self.assertIn("compose/caddy-public/compose.yaml", unit)
        self.assertIn("caddy-public", str(GUARD.STATE))
        self.assertIn("caddy-public", str(GUARD.COMPOSE))


class StorageGuardTests(unittest.TestCase):
    def response(self, argv, *, active=False, label="storage_sdcard", extra_mount=False):
        if argv[0] == "/usr/bin/systemctl":
            return subprocess.CompletedProcess(argv, 0 if active else 3, "", "")
        if argv[0] == "/usr/bin/ls":
            return subprocess.CompletedProcess(argv, 0, "", "")
        if argv[0] == "/usr/bin/findmnt":
            output = label if "--mountpoint" in argv else f"{GUARD.MOUNT} {label}"
            return subprocess.CompletedProcess(argv, 0, output, "")
        if argv[0] == "/usr/bin/docker-compose":
            expected = {
                "/data": (GUARD.STATE / "data", False),
                "/config": (GUARD.STATE / "config", False),
                "/etc/caddy/Caddyfile": (GUARD.COMPOSE / "Caddyfile", True),
            }
            volumes = [{"target": target, "source": str(source), "type": "bind",
                        "read_only": readonly, "bind": {"create_host_path": False}}
                       for target, (source, readonly) in expected.items()]
            if extra_mount:
                volumes.append({"target": "/var/run/docker.sock", "type": "bind"})
            data = {"services": {"server": {"volumes": volumes}}}
            return subprocess.CompletedProcess(argv, 0, json.dumps(data), "")
        self.fail(f"Unexpected command: {argv[0]}")

    def run_guard(self, **kwargs):
        with patch.object(GUARD, "run", side_effect=lambda argv: self.response(argv, **kwargs)), \
             patch.object(Path, "is_dir", return_value=True), \
             patch.object(Path, "is_symlink", return_value=False), \
             patch.object(Path, "resolve", lambda value: value):
            GUARD.main()

    def test_accepts_original_sd_storage(self):
        self.run_guard()

    def test_rejects_active_private_profile(self):
        with self.assertRaisesRegex(SystemExit, "Legacy Forgejo"):
            self.run_guard(active=True)

    def test_rejects_wrong_mount(self):
        with self.assertRaisesRegex(SystemExit, "Expected ext4"):
            self.run_guard(label="wrong_disk")

    def test_rejects_unexpected_mount(self):
        with self.assertRaisesRegex(SystemExit, "Unexpected persistent mounts"):
            self.run_guard(extra_mount=True)


if __name__ == "__main__":
    unittest.main()
