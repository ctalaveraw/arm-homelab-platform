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
AUTH = "${STATE_SERVICES_ROOT:?Set STATE_SERVICES_ROOT}/prometheus-auth"
CREDENTIALS = "/run/secrets/platform-observer"


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
        "group_add": ["29012"],
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
    require(len(bindings) == 3, "Unexpected volume count")

    by_target = {
        volume["target"]: volume
        for volume in bindings
    }

    require(len(by_target) == 3, "Duplicate volume target")
    require(
        set(by_target) == {
            "/prometheus",
            "/etc/prometheus/prometheus.yml",
            CREDENTIALS,
        },
        "Unexpected volume targets",
    )

    for target, source in {
        "/prometheus": STATE,
        "/etc/prometheus/prometheus.yml": "./prometheus.yml",
        CREDENTIALS: AUTH,
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

    require(
        by_target[CREDENTIALS].get("read_only") is True,
        "Observer mount must be read-only",
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
            "missing observer group": ("group_add", []),
            "wrong observer group": ("group_add", ["65534"]),
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
            (CREDENTIALS, "read_only", False),
            (CREDENTIALS, "source", "/tmp/untrusted"),
            (CREDENTIALS, "bind", {}),
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

    def test_observer_scrape_contract(self):
        jobs = yaml.safe_load((OBS / "prometheus.yml").read_text())["scrape_configs"]
        by_name = {job["job_name"]: job for job in jobs}
        paths = {
            "kubernetes-apiserver": "/metrics",
            "flux-source-controller": (
                "/api/v1/namespaces/flux-system/services/"
                "http:flux-source-metrics:metrics/proxy/metrics"
            ),
            "flux-kustomize-controller": (
                "/api/v1/namespaces/flux-system/services/"
                "http:flux-kustomize-metrics:metrics/proxy/metrics"
            ),
        }
        self.assertEqual(set(by_name), {
            "prometheus", "r5c", "pi-nodes", *paths,
        })
        for name, path in paths.items():
            with self.subTest(job=name):
                job = by_name[name]
                self.assertEqual(job["scheme"], "https")
                self.assertEqual(job["metrics_path"], path)
                self.assertEqual(job["scrape_interval"], "60s")
                self.assertEqual(job["scrape_timeout"], "20s")
                self.assertLessEqual(job["sample_limit"], 5000)
                self.assertEqual(job["static_configs"], [{"targets": ["10.0.0.5:6443"]}])
                self.assertEqual(job["tls_config"], {
                    "ca_file": CREDENTIALS + "/ca.crt",
                    "cert_file": CREDENTIALS + "/client.crt",
                    "key_file": CREDENTIALS + "/client.key",
                })
                self.assertEqual(len(job["metric_relabel_configs"]), 1)
                rule = job["metric_relabel_configs"][0]
                self.assertEqual(rule["action"], "keep")
                self.assertEqual(rule["source_labels"], ["__name__"])
                self.assertIsNone(re.fullmatch(rule["regex"], "suspicious_metric"))
                if name == "kubernetes-apiserver":
                    self.assertIsNone(re.fullmatch(
                        rule["regex"], "apiserver_request_duration_seconds_bucket"
                    ))
                else:
                    self.assertIsNotNone(re.fullmatch(
                        rule["regex"], "gotk_reconcile_duration_seconds_bucket"
                    ))

    def test_observer_guard_and_provisioning_contract(self):
        guard = (OBS / "check-storage.py").read_text()
        for expected in ("AUTH_GID = 29012", "0o640", "0o750", "sslclient",
                         '"-checkend", "86400"', '"/run/secrets/platform-observer"'):
            self.assertIn(expected, guard)
        playbook = yaml.safe_load((ROOT / "ansible/playbooks/07-prometheus.yml").read_text())
        tasks = playbook[1]["tasks"]
        self.assertTrue(any(t.get("ansible.builtin.group", {}).get("gid") == 29012
                            for t in tasks))
        copies = [t for t in tasks if t.get("name") == "Install protected observer runtime copies"]
        self.assertEqual(len(copies), 1)
        task = copies[0]
        self.assertTrue(task["no_log"])
        self.assertEqual(task["ansible.builtin.copy"]["mode"], "0640")
        self.assertTrue(task["ansible.builtin.copy"]["remote_src"])

    def test_prometheus_handler_ordering(self):
        playbook = yaml.safe_load(
            (ROOT / "ansible/playbooks/07-prometheus.yml").read_text()
        )
        tasks = playbook[1]["tasks"]
        names = [task.get("name") for task in tasks]

        def position(name):
            return names.index(name)

        self.assertEqual(
            sum(
                t.get("ansible.builtin.meta") == "flush_handlers"
                for t in tasks
            ),
            1,
        )

        sequence = [
            "Install protected observer runtime copies",
            "Install Prometheus storage guard",
            "Verify runtime observer credentials with storage guard",
            "Track Prometheus scrape configuration",
            "Track Prometheus Compose deployment configuration",
            "Apply pending Prometheus restart",
            "Enable and start guarded Prometheus",
            "Verify Prometheus HTTP readiness",
        ]

        positions = [position(name) for name in sequence]
        self.assertEqual(positions, sorted(positions))

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
