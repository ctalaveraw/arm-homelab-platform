"""R5C native host-metrics deployment contracts."""

import json
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


class R5CHostMetricsTests(unittest.TestCase):
    def test_native_service_security(self):
        unit = (
            ROOT / "ansible/files/node-exporter.service"
        ).read_text()
        for expected in (
            "User=node-exporter",
            "NoNewPrivileges=true",
            "CapabilityBoundingSet=",
            "ProtectSystem=strict",
            "MemoryMax=96M",
            "TasksMax=64",
            "--web.listen-address=10.0.0.50:9100",
        ):
            self.assertIn(expected, unit)
        self.assertNotIn("User=root", unit)

    def test_verified_binary_and_ansible_lifecycle(self):
        playbook = yaml.safe_load(
            (ROOT / "ansible/playbooks/09-node-exporter.yml").read_text()
        )
        self.assertEqual(playbook[0]["import_playbook"], "00-preflight.yml")
        tasks = playbook[1]["tasks"]
        downloads = [
            task["ansible.builtin.get_url"]
            for task in tasks
            if "ansible.builtin.get_url" in task
        ]
        self.assertEqual(len(downloads), 1)
        self.assertEqual(
            downloads[0]["checksum"],
            "sha256:ad35b605f9954b9f1ffddf5ba054bdc5a98d790b9eae5291e1eeb83f1ecbd0e7",
        )
        self.assertTrue(
            any(
                task.get("ansible.builtin.systemd_service", {}).get("name")
                == "node-exporter.service"
                for task in tasks
            )
        )

    def test_dedicated_identity_and_scoped_sd_acl(self):
        unit = (
            ROOT / "ansible/files/node-exporter.service"
        ).read_text()

        self.assertIn("User=node-exporter", unit)
        self.assertIn("Group=node-exporter", unit)
        self.assertNotIn("User=nobody", unit)
        self.assertNotIn("User=runner", unit)

        playbook = yaml.safe_load(
            (ROOT / "ansible/playbooks/09-node-exporter.yml").read_text()
        )
        tasks = playbook[1]["tasks"]

        identities = [
            task["ansible.builtin.user"]
            for task in tasks
            if "ansible.builtin.user" in task
        ]
        self.assertEqual(len(identities), 1)
        self.assertEqual(identities[0]["name"], "node-exporter")
        self.assertFalse(identities[0]["create_home"])

        acl_commands = [
            task["ansible.builtin.command"]["argv"]
            for task in tasks
            if isinstance(task.get("ansible.builtin.command"), dict)
            and "argv" in task["ansible.builtin.command"]
            and task["ansible.builtin.command"]["argv"][0]
            == "/usr/bin/setfacl"
        ]
        expected_acl_commands = [
            [
                "/usr/bin/setfacl",
                "-m",
                "u:node-exporter:--x",
                "/srv/storage",
            ],
            [
                "/usr/bin/setfacl",
                "-m",
                "u:node-exporter:--x",
                "/srv/storage/state",
            ],
        ]
        self.assertEqual(acl_commands, expected_acl_commands)

        self.assertTrue(
            any(
                task.get("become_user") == "node-exporter"
                and task.get("failed_when")
                == "exporter_secret_denial.rc == 0"
                for task in tasks
            )
        )

    def test_prometheus_job_and_dashboard(self):
        config = yaml.safe_load(
            (ROOT / "compose/observability/prometheus.yml").read_text()
        )
        jobs = {
            job["job_name"]: job
            for job in config["scrape_configs"]
        }
        self.assertEqual(set(jobs), {"prometheus", "r5c"})
        self.assertEqual(
            jobs["r5c"]["static_configs"][0]["targets"],
            ["10.0.0.50:9100"],
        )
        dashboard = json.loads(
            (
                ROOT / "compose/observability/grafana/dashboards/r5c-host.json"
            ).read_text()
        )
        self.assertEqual(dashboard["uid"], "arm-r5c-host")
        self.assertEqual(len(dashboard["panels"]), 6)

    def test_scrape_change_triggers_ansible_restart(self):
        playbook = yaml.safe_load(
            (ROOT / "ansible/playbooks/07-prometheus.yml").read_text()
        )
        tasks = playbook[1]["tasks"]
        self.assertTrue(
            any(
                task.get("ansible.builtin.copy", {}).get("dest")
                == "/etc/observability-prometheus-config.sha256"
                and task.get("notify") == "Restart Prometheus"
                for task in tasks
            )
        )


if __name__ == "__main__":
    unittest.main()
