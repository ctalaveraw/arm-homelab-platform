"""Portable, adversarial contracts for PLAT-012 Prometheus."""

import copy
import re
import unittest
from pathlib import Path

import yaml
from test_compose_contracts import SERVICES

ROOT = Path(__file__).resolve().parents[3]
OBS = ROOT / "compose/observability"
STATE = "${STATE_SERVICES_ROOT:?Set STATE_SERVICES_ROOT}/prometheus"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_prometheus(config):
    """Check source YAML, avoiding Compose JSON serialization differences."""
    require(config.get("name") == "observability", "Wrong project")
    service = config["services"]["prometheus"]

    require(
        re.fullmatch(
            r"prom/prometheus:v\d+\.\d+\.\d+",
            service.get("image", ""),
        ),
        "Prometheus image must use a versioned tag",
    )

    for key, expected in {
        "restart": "no",
        "user": "65534:65534",
        "read_only": True,
        "cap_drop": ["ALL"],
        "security_opt": ["no-new-privileges:true"],
        "mem_limit": "384m",
        "pids_limit": 128,
    }.items():
        require(service.get(key) == expected, f"Unsafe {key}")

    require(service.get("privileged") is not True, "Privileged service")
    require(service.get("network_mode") != "host", "Host networking")
    require(
        service.get("ports") == ["127.0.0.1:9090:9090"],
        "Unsafe host port",
    )
    require(
        "/tmp:size=16m,mode=1777" in service.get("tmpfs", []),
        "Missing tmpfs",
    )

    bindings = service.get("volumes", [])
    require(len(bindings) == 2, "Unexpected volume count")

    by_target = {
        volume["target"]: volume
        for volume in bindings
    }

    require(len(by_target) == 2, "Duplicate volume target")
    require(
        set(by_target) == {
            "/prometheus",
            "/etc/prometheus/prometheus.yml",
        },
        "Unexpected volume targets",
    )

    for target, source in {
        "/prometheus": STATE,
        "/etc/prometheus/prometheus.yml": "./prometheus.yml",
    }.items():
        binding = by_target[target]

        require(
            binding.get("type") == "bind",
            f"Unsafe volume type: {target}",
        )
        require(
            binding.get("source") == source,
            f"Unsafe source: {target}",
        )
        require(
            binding.get("bind", {}).get("create_host_path") is False,
            f"Auto-creation permitted: {target}",
        )

    require(
        by_target[
            "/etc/prometheus/prometheus.yml"
        ].get("read_only") is True,
        "Config must be read-only",
    )

    args = set(service.get("command", []))

    require(
        {
            "--config.file=/etc/prometheus/prometheus.yml",
            "--storage.tsdb.path=/prometheus",
            "--storage.tsdb.retention.time=48h",
            "--storage.tsdb.retention.size=512MB",
        } <= args,
        "Missing bounded TSDB configuration",
    )


class ObservabilityContractTests(unittest.TestCase):
    def setUp(self):
        self.config = yaml.safe_load(
            (OBS / "compose.yml").read_text()
        )

    def test_all_compose_projects_are_registered_for_contracts(self):
        discovered = {
            item.parent.name
            for item in (ROOT / "compose").glob("*/compose.yml")
        }

        self.assertEqual(
            discovered,
            set(SERVICES) | {"observability"},
        )

    def test_prometheus_contract(self):
        validate_prometheus(self.config)

    def test_unsafe_mutations_are_rejected(self):
        changes = {
            "docker restart bypass": ("restart", "always"),
            "root process": ("user", "0:0"),
            "privileged runtime": ("privileged", True),
            "lost capability restriction": ("cap_drop", []),
            "lost read-only root": ("read_only", False),
            "unbounded memory": ("mem_limit", None),
            "exposed LAN port": (
                "ports",
                ["0.0.0.0:9090:9090"],
            ),
        }

        for case, (field, value) in changes.items():
            with self.subTest(case=case):
                bad = copy.deepcopy(self.config)
                bad["services"]["prometheus"][field] = value

                with self.assertRaises(ValueError):
                    validate_prometheus(bad)

        for target, field, value in [
            ("/prometheus", "source", "/tmp/prometheus"),
            ("/prometheus", "bind", {}),
            (
                "/etc/prometheus/prometheus.yml",
                "read_only",
                False,
            ),
        ]:
            with self.subTest(target=target, field=field):
                bad = copy.deepcopy(self.config)

                volume = next(
                    v
                    for v in bad["services"]["prometheus"]["volumes"]
                    if v["target"] == target
                )

                volume[field] = value

                with self.assertRaises(ValueError):
                    validate_prometheus(bad)

    def test_systemd_and_ansible_guard_boundary(self):
        unit = (OBS / "prometheus.service").read_text()

        for required in (
            "RequiresMountsFor=/srv/storage/state/services/prometheus",
            "ExecStartPre=/usr/local/sbin/prometheus-check-storage",
            "Environment=STATE_SERVICES_ROOT=/srv/storage/state/services",
            " up -d prometheus",
            " stop prometheus",
        ):
            self.assertIn(required, unit)

        playbook = yaml.safe_load(
            (
                ROOT / "ansible/playbooks/07-prometheus.yml"
            ).read_text()
        )

        self.assertEqual(
            playbook[0]["import_playbook"],
            "00-preflight.yml",
        )

        tasks = playbook[1]["tasks"]

        copies = [
            task["ansible.builtin.copy"]["dest"]
            for task in tasks
            if "ansible.builtin.copy" in task
        ]

        self.assertIn(
            "/usr/local/sbin/prometheus-check-storage",
            copies,
        )

        service_tasks = [
            task["ansible.builtin.systemd_service"]
            for task in tasks
            if "ansible.builtin.systemd_service" in task
        ]

        self.assertTrue(
            any(
                task.get("name") == "prometheus.service"
                and task.get("enabled") is True
                and task.get("state") == "started"
                for task in service_tasks
            )
        )

        config_tasks = [
            task["ansible.builtin.file"]
            for task in tasks
            if "ansible.builtin.file" in task
        ]

        self.assertTrue(
            any(
                task.get("path")
                == "/srv/platform/compose/observability/prometheus.yml"
                and task.get("state") == "file"
                and task.get("mode") == "0644"
                for task in config_tasks
            )
        )

        self.assertTrue(
            any(
                task.get("ansible.builtin.uri", {}).get("url")
                == "http://127.0.0.1:9090/-/ready"
                for task in tasks
            )
        )

        self.assertTrue(
            any(
                handler.get("name") == "Restart Prometheus"
                for handler in playbook[1]["handlers"]
            )
        )


if __name__ == "__main__":
    unittest.main()
