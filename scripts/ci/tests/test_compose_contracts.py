"""Portable regression tests for stateful Compose safety contracts."""

import re
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]

SERVICES = {
    "gitea": "/data",
    "gotify": "/app/data",
    "uptime-kuma": "/app/data",
    "apt-cacher-ng": "/var/cache/apt-cacher-ng",
}


class ComposeContractTests(unittest.TestCase):

    def load_service(self, name):
        manifest = ROOT / "compose" / name / "compose.yml"
        config = yaml.safe_load(manifest.read_text())
        return config["services"]["server"]

    def test_docker_cannot_bypass_guarded_startup(self):
        for name in SERVICES:
            with self.subTest(service=name):
                service = self.load_service(name)
                self.assertEqual(service["restart"], "no")
                self.assertIsNot(service.get("privileged", False), True)

    def test_persistent_storage_contract(self):
        for name, target in SERVICES.items():
            with self.subTest(service=name):
                service = self.load_service(name)

                volumes = service.get("volumes", [])
                self.assertEqual(len(volumes), 1)

                volume = volumes[0]

                self.assertEqual(volume["type"], "bind")
                self.assertEqual(
                    volume["source"],
                    "${STATE_SERVICES_ROOT:?Set STATE_SERVICES_ROOT}/"
                    + name,
                )
                self.assertEqual(volume["target"], target)
                self.assertIs(
                    volume["bind"]["create_host_path"],
                    False,
                )

    def test_ports_require_explicit_bind_address(self):
        pattern = re.compile(
            r"^\$\{[A-Z_]*BIND_IP:\?[^}]+\}:"
        )

        for name in SERVICES:
            with self.subTest(service=name):
                ports = self.load_service(name)["ports"]

                self.assertTrue(ports)

                for port in ports:
                    self.assertRegex(port, pattern)


if __name__ == "__main__":
    unittest.main()
