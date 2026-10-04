"""Portable regression tests for stateful Compose safety contracts."""

import re
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]

# Service name -> expected persistent container mount.
SERVICES = {
    "gitea": "/data",
    "gitea-runner": "/data",
    "gotify": "/app/data",
    "uptime-kuma": "/app/data",
    "apt-cacher-ng": "/var/cache/apt-cacher-ng",
}


class ComposeContractTests(unittest.TestCase):

    def load_service(self, name):
        """Load the actual Compose service without interpolating secrets."""
        manifest = ROOT / "compose" / name / "compose.yml"
        config = yaml.safe_load(manifest.read_text())

        # The runner has its own service name to avoid colliding with
        # Gitea's existing 'server' DNS alias on gitea_default.
        service_name = "runner" if name == "gitea-runner" else "server"

        return config["services"][service_name]

    def test_docker_cannot_bypass_guarded_startup(self):
        """Systemd, not Docker restart policy, owns service activation."""
        for name in SERVICES:
            with self.subTest(service=name):
                service = self.load_service(name)

                self.assertEqual(service["restart"], "no")
                self.assertIsNot(service.get("privileged", False), True)

    def test_persistent_storage_contract(self):
        """Every stateful service must use its explicit SD bind source."""
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
        """Applications require explicit IP bindings; runner exposes none."""
        pattern = re.compile(
            r"^\$\{[A-Z_]*BIND_IP:\?[^}]+\}:"
        )

        for name in SERVICES:
            with self.subTest(service=name):
                service = self.load_service(name)
                ports = service.get("ports", [])

                if name == "gitea-runner":
                    # The runner initiates outbound connections to Gitea.
                    # It must never publish an inbound host port.
                    self.assertFalse(ports)
                    continue

                # Network-facing application services must publish ports
                # with an explicit, non-empty host bind address.
                self.assertTrue(ports)

                for port in ports:
                    self.assertRegex(port, pattern)

    def test_runner_has_no_host_privileges(self):
        """Keep the trusted validation worker minimally privileged."""
        service = self.load_service("gitea-runner")

        self.assertEqual(service["user"], "10001:10001")
        self.assertEqual(service["cap_drop"], ["ALL"])
        self.assertEqual(
            service["security_opt"],
            ["no-new-privileges:true"],
        )

        self.assertFalse(service.get("privileged", False))
        self.assertFalse(service.get("ports", []))
        self.assertNotEqual(service.get("network_mode"), "host")

        # No access to the R5C production Docker daemon.
        for volume in service.get("volumes", []):
            self.assertNotEqual(
                volume.get("source"),
                "/var/run/docker.sock",
            )


if __name__ == "__main__":
    unittest.main()
