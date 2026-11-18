"""Migration separation, ingress trust, and fail-closed certificate storage."""

import copy
import importlib.util
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[3]


def manifest(name):
    return yaml.safe_load((ROOT / "compose" / name / "compose.yml").read_text())


class ForgejoIngressTests(unittest.TestCase):
    def test_migration_has_separate_state_and_ports(self):
        config = manifest("forgejo")
        server = config["services"]["server"]
        self.assertEqual(server["image"], "codeberg.org/forgejo/forgejo:15.0.11")
        self.assertEqual(
            server["volumes"][0]["source"],
            "${STATE_SERVICES_ROOT:?Set STATE_SERVICES_ROOT}/forgejo",
        )
        self.assertIn("3001", server["ports"][0])
        self.assertIn("2223", server["ports"][1])
        self.assertFalse(any("/gitea" in str(v) for v in server["volumes"]))

    def test_proxy_authentication_is_disabled_and_trust_is_exact(self):
        env = manifest("forgejo")["services"]["server"]["environment"]
        self.assertEqual(env["FORGEJO__service__ENABLE_REVERSE_PROXY_AUTHENTICATION"], "false")
        self.assertEqual(
            env["FORGEJO__security__REVERSE_PROXY_TRUSTED_PROXIES"],
            "${PROXY_CONTAINER_IP:?Set PROXY_CONTAINER_IP}/32",
        )
        self.assertEqual(env["FORGEJO__service__DISABLE_REGISTRATION"], "true")
        self.assertEqual(env["FORGEJO__service__REQUIRE_SIGNIN_VIEW"], "true")

    def test_caddy_has_no_administration_or_backend_publication(self):
        config = manifest("caddy")
        service = config["services"]["server"]
        self.assertEqual(service["restart"], "no")
        self.assertEqual(service["ports"], [
            "${PROXY_BIND_IP:?Set PROXY_BIND_IP}:80:80/tcp",
            "${PROXY_BIND_IP:?Set PROXY_BIND_IP}:443:443/tcp",
        ])
        self.assertTrue(service["read_only"])
        self.assertEqual(service["cap_drop"], ["ALL"])
        self.assertEqual(service["cap_add"], ["NET_BIND_SERVICE"])
        self.assertNotEqual(service.get("network_mode"), "host")
        self.assertTrue(config["networks"]["ingress"]["external"])
        self.assertFalse(any("docker.sock" in str(v) for v in service["volumes"]))
        self.assertIn("reverse_proxy forgejo:3000", (ROOT / "compose/caddy/Caddyfile").read_text())


class CaddyGuardTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("caddy_guard", ROOT / "compose/caddy/check-storage.py")
        self.guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.guard)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.guard.MOUNT = Path(self.tmp.name) / "state"
        self.guard.STATE = self.guard.MOUNT / "services/caddy"
        self.guard.COMPOSE = Path(self.tmp.name) / "compose"
        for path in [self.guard.STATE / "data", self.guard.STATE / "config"]:
            path.mkdir(parents=True, exist_ok=True)
        self.volumes = [
            {"type": "bind", "source": str(source), "target": target,
             "read_only": readonly, "bind": {"create_host_path": False}}
            for source, target, readonly in [
                (self.guard.STATE / "data", "/data", False),
                (self.guard.STATE / "config", "/config", False),
                (self.guard.COMPOSE / "Caddyfile", "/etc/caddy/Caddyfile", True),
            ]
        ]

    def exercise(self, *, label="storage_sdcard", volumes=None):
        def command(argv):
            output = ""
            if argv[0].endswith("findmnt"):
                output = label if "--mountpoint" in argv else f"{self.guard.MOUNT} {label}"
            elif argv[0].endswith("docker-compose"):
                output = json.dumps({"services": {"server": {"volumes": self.volumes if volumes is None else volumes}}})
            return subprocess.CompletedProcess(argv, 0, stdout=output, stderr="")

        with patch.object(self.guard, "run", side_effect=command), redirect_stdout(StringIO()):
            self.guard.main()

    def test_valid_mounted_certificate_state_passes(self):
        self.exercise()

    def test_wrong_filesystem_fails(self):
        with self.assertRaisesRegex(SystemExit, "filesystem"):
            self.exercise(label="rootfs")

    def test_redirected_certificate_directory_fails(self):
        data = self.guard.STATE / "data"
        data.rmdir()
        data.symlink_to(self.guard.STATE / "config", target_is_directory=True)
        with self.assertRaisesRegex(SystemExit, "redirected"):
            self.exercise()

    def test_wrong_bind_source_or_writable_configuration_fails(self):
        for index, key, value in [(0, "source", "/tmp/data"), (2, "read_only", False)]:
            bad = copy.deepcopy(self.volumes)
            bad[index][key] = value
            with self.subTest(index=index, field=key), self.assertRaisesRegex(SystemExit, "contract"):
                self.exercise(volumes=bad)

    def test_missing_or_duplicate_certificate_mount_fails(self):
        for bad in [self.volumes[:2], [self.volumes[0], self.volumes[0], self.volumes[2]]]:
            with self.assertRaisesRegex(SystemExit, "mounts"):
                self.exercise(volumes=bad)


if __name__ == "__main__":
    unittest.main()
