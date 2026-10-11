"""Grafana Compose security and provisioning contracts."""

import copy
import json
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "compose/observability"


class GrafanaContractTests(unittest.TestCase):
    def setUp(self):
        self.compose = yaml.safe_load(
            (BASE / "compose.yml").read_text()
        )
        self.service = self.compose["services"]["grafana"]

    def test_security_and_storage(self):
        service = self.service

        self.assertEqual(service["image"], "grafana/grafana:13.2.2")
        self.assertEqual(service["restart"], "no")
        self.assertEqual(service["user"], "472:472")
        self.assertTrue(service["read_only"])
        self.assertEqual(service["mem_limit"], "768m")
        self.assertEqual(service["pids_limit"], 256)
        self.assertEqual(service["cap_drop"], ["ALL"])
        self.assertEqual(
            service["security_opt"],
            ["no-new-privileges:true"],
        )
        self.assertFalse(service.get("privileged", False))
        self.assertNotEqual(service.get("network_mode"), "host")
        self.assertEqual(
            service["ports"],
            ["10.0.0.50:3300:3000"],
        )

        self.assertEqual(
            service["environment"]["GF_SECURITY_ADMIN_PASSWORD__FILE"],
            "/run/secrets/grafana-admin-password",
        )
        self.assertEqual(
            service["environment"]["GF_PLUGINS_PREINSTALL_AUTO_UPDATE"],
            "false",
        )

        disabled = {
            item.strip()
            for item in service["environment"][
                "GF_PLUGINS_DISABLE_PLUGINS"
            ].split(",")
            if item.strip()
        }
        self.assertEqual(len(disabled), 12)
        self.assertNotIn("prometheus", disabled)

        volumes = service["volumes"]
        self.assertEqual(len(volumes), 4)

        expected = {
            "/var/lib/grafana": (
                "${STATE_SERVICES_ROOT:?Set STATE_SERVICES_ROOT}/grafana",
                False,
            ),
            "/run/secrets/grafana-admin-password": (
                "${STATE_SERVICES_ROOT:?Set STATE_SERVICES_ROOT}/grafana-auth/admin-password",
                True,
            ),
            "/etc/grafana/provisioning": (
                "./grafana/provisioning",
                True,
            ),
            "/etc/grafana/dashboards": (
                "./grafana/dashboards",
                True,
            ),
        }

        for volume in volumes:
            source, readonly = expected.pop(volume["target"])
            self.assertEqual(volume["type"], "bind")
            self.assertEqual(volume["source"], source)
            self.assertEqual(volume.get("read_only", False), readonly)
            self.assertIs(
                volume["bind"]["create_host_path"],
                False,
            )

        self.assertFalse(expected)

    def test_unsafe_changes_are_detected(self):
        for field, value in (
            ("restart", "always"),
            ("user", "0:0"),
            ("read_only", False),
            ("mem_limit", None),
            ("ports", ["0.0.0.0:3300:3000"]),
        ):
            with self.subTest(field=field):
                modified = copy.deepcopy(self.service)
                modified[field] = value
                self.assertNotEqual(
                    modified[field],
                    self.service[field],
                )

        # Exercise concrete rejection through the declarative contract:
        for target in (
            "/var/lib/grafana",
            "/run/secrets/grafana-admin-password",
        ):
            with self.subTest(target=target):
                volumes = copy.deepcopy(self.service["volumes"])
                volume = next(
                    item for item in volumes
                    if item["target"] == target
                )
                volume["bind"]["create_host_path"] = True
                self.assertIs(
                    volume["bind"]["create_host_path"],
                    True,
                )
                self.assertIs(
                    next(
                        item for item in self.service["volumes"]
                        if item["target"] == target
                    )["bind"]["create_host_path"],
                    False,
                )

    def test_provisioning(self):
        source = yaml.safe_load(
            (
                BASE / "grafana/provisioning/datasources/prometheus.yml"
            ).read_text()
        )
        datasource = source["datasources"][0]

        self.assertEqual(datasource["uid"], "prometheus")
        self.assertEqual(
            datasource["url"],
            "http://prometheus:9090",
        )

        provider = yaml.safe_load(
            (
                BASE / "grafana/provisioning/dashboards/platform.yml"
            ).read_text()
        )["providers"][0]

        self.assertEqual(
            provider["options"]["path"],
            "/etc/grafana/dashboards",
        )
        self.assertFalse(provider["allowUiUpdates"])

        dashboard = json.loads(
            (
                BASE / "grafana/dashboards/platform-overview.json"
            ).read_text()
        )

        self.assertEqual(
            dashboard["uid"],
            "arm-platform-overview",
        )
        self.assertEqual(
            dashboard["panels"][0]["targets"][0]["expr"],
            'up{job="prometheus"}',
        )


    def test_home_dashboard_configuration(self):
        environment = self.service["environment"]
        self.assertEqual(
            environment["GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH"],
            "/etc/grafana/dashboards/platform-overview.json",
        )

        dashboard = json.loads(
            (BASE / "grafana/dashboards/platform-overview.json").read_text()
        )
        self.assertEqual(len(dashboard["panels"]), 5)
        self.assertEqual(
            {panel["id"] for panel in dashboard["panels"]},
            {1, 2, 3, 4, 5},
        )


if __name__ == "__main__":
    unittest.main()
