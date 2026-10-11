"""Contracts for the three physical Pi telemetry exporters."""

import json
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


class PiExporterTests(unittest.TestCase):
    def test_inventory_has_exact_verified_hosts(self):
        text = (
            ROOT / "ansible/inventories/pi-nodes.ini"
        ).read_text()
        for host, ip, user in (
            ("ci-controller-01", "10.0.0.5", "ct"),
            ("ci-controller-02", "10.0.0.6", "runner"),
            ("ci-controller-04", "10.0.0.8", "runner"),
        ):
            self.assertIn(
                f"{host} exporter_address={ip}",
                text,
            )
        self.assertNotIn("ansible_host=", text)
        self.assertNotIn("ansible_user=", text)
        self.assertIn("StrictHostKeyChecking=yes", text)
        self.assertIn("BatchMode=yes", text)

    def test_exporter_security_and_budgets(self):
        unit = (
            ROOT / "ansible/templates/pi-node-exporter.service.j2"
        ).read_text()
        for value in (
            "User=node-exporter",
            "Group=node-exporter",
            "NoNewPrivileges=true",
            "CapabilityBoundingSet=",
            "ProtectSystem=strict",
            "ProtectHome=true",
            "MemoryMax=64M",
            "TasksMax=64",
            "--web.listen-address={{ exporter_address }}:9100",
        ):
            self.assertIn(value, unit)
        self.assertNotIn("User=root", unit)

    def test_serial_deployment_and_integrity_pin(self):
        plays = yaml.safe_load(
            (ROOT / "ansible/playbooks/10-pi-exporters.yml").read_text()
        )
        self.assertEqual(len(plays), 1)
        play = plays[0]
        self.assertEqual(play["hosts"], "pi_nodes")
        self.assertEqual(play["serial"], 1)
        self.assertTrue(play["become"])

        downloads = [
            task["ansible.builtin.get_url"]
            for task in play["tasks"]
            if "ansible.builtin.get_url" in task
        ]
        self.assertEqual(len(downloads), 1)
        self.assertEqual(
            downloads[0]["checksum"],
            "sha256:ad35b605f9954b9f1ffddf5ba054bdc5a98d790b9eae5291e1eeb83f1ecbd0e7",
        )

        names = [task["name"] for task in play["tasks"]]
        self.assertIn("Verify kubelet remains active", names)

    def test_scrape_targets_and_labels(self):
        config = yaml.safe_load(
            (ROOT / "compose/observability/prometheus.yml").read_text()
        )
        jobs = {
            job["job_name"]: job
            for job in config["scrape_configs"]
        }
        self.assertTrue(
            {"prometheus", "r5c", "pi-nodes"} <= set(jobs)
        )
        self.assertEqual(
            len(config["scrape_configs"]), len(jobs)
        )

        groups = jobs["pi-nodes"]["static_configs"]
        self.assertEqual(
            {
                (
                    group["targets"][0],
                    group["labels"]["node"],
                    group["labels"]["role"],
                )
                for group in groups
            },
            {
                ("10.0.0.5:9100", "ci-controller-01", "control-plane"),
                ("10.0.0.6:9100", "ci-controller-02", "worker"),
                ("10.0.0.8:9100", "ci-controller-04", "worker"),
            },
        )

        dashboard = json.loads(
            (
                ROOT
                / "compose/observability/grafana/dashboards/pi-nodes.json"
            ).read_text()
        )
        self.assertEqual(dashboard["uid"], "arm-pi-nodes")
        self.assertEqual(len(dashboard["panels"]), 6)

    def test_guard_and_ansible_register_dashboard(self):
        guard = (
            ROOT / "compose/observability/grafana-check-storage.py"
        ).read_text()
        self.assertIn('SOURCE / "dashboards/pi-nodes.json"', guard)

        playbook = yaml.safe_load(
            (ROOT / "ansible/playbooks/08-grafana.yml").read_text()
        )
        tasks = playbook[1]["tasks"]
        self.assertTrue(
            any(
                "pi-nodes.json" in str(task)
                for task in tasks
            )
        )


if __name__ == "__main__":
    unittest.main()
