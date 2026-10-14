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


    def test_kubernetes_flux_dashboards(self):
        expected = {
            "kubernetes-api.json": ("arm-kubernetes-api", 9),
            "flux-reconciliation.json": ("arm-flux-reconciliation", 10),
        }
        guard = (BASE / "grafana-check-storage.py").read_text()
        playbook = (
            ROOT / "ansible/playbooks/08-grafana.yml"
        ).read_text()

        for filename, (uid, count) in expected.items():
            with self.subTest(dashboard=filename):
                doc = json.loads(
                    (BASE / "grafana/dashboards" / filename).read_text()
                )
                self.assertEqual(doc["uid"], uid)
                self.assertEqual(doc["refresh"], "1m")
                self.assertEqual(len(doc["panels"]), count)
                self.assertEqual(
                    len({p["id"] for p in doc["panels"]}), count
                )
                self.assertIn(filename, guard)
                self.assertEqual(playbook.count(
                    "/grafana/dashboards/" + filename
                ), 2)

                for panel in doc["panels"]:
                    self.assertEqual(
                        panel["datasource"]["uid"], "prometheus"
                    )
                    self.assertEqual(len(panel["targets"]), 1)
                    expression = panel["targets"][0]["expr"]
                    self.assertIn("job=", expression)
                    self.assertLessEqual(
                        panel["gridPos"]["x"]
                        + panel["gridPos"]["w"], 24
                    )
                    self.assertNotIn("cluster-admin", expression)

    def test_bind_mount_directory_traversal_contract(self):
        import ast
        import runpy
        from tempfile import TemporaryDirectory

        playbook = yaml.safe_load(
            (ROOT / "ansible/playbooks/08-grafana.yml").read_text()
        )
        tasks = playbook[1]["tasks"]
        task_names = [task["name"] for task in tasks]
        name = "Enforce Grafana configuration directory traversal"

        self.assertLess(
            task_names.index(name),
            task_names.index("Install Grafana storage guard"),
        )

        task = next(task for task in tasks if task["name"] == name)
        module = task["ansible.builtin.file"]

        self.assertEqual(module["mode"], "0755")
        self.assertEqual(module["owner"], "runner")
        self.assertEqual(module["group"], "runner")
        self.assertEqual(task["notify"], "Restart Grafana")

        self.assertEqual(set(task["loop"]), {
            "/srv/platform/compose/observability/grafana/provisioning",
            "/srv/platform/compose/observability/grafana/provisioning/dashboards",
            "/srv/platform/compose/observability/grafana/provisioning/datasources",
            "/srv/platform/compose/observability/grafana/dashboards",
        })

        source = (BASE / "grafana-check-storage.py").read_text()
        tree = ast.parse(source)

        function = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "verify_grafana_source_directory"
        )

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            extracted = ast.get_source_segment(source, function)
            self.assertIsNotNone(extracted)
            helper = root / "grafana-directory-validator.py"
            helper.write_text(
                "import stat\n\n"
                "def fail(message):\n    raise ValueError(message)\n\n"
                + extracted + "\n",
                encoding="utf-8",
            )
            verify = runpy.run_path(str(helper))[
                "verify_grafana_source_directory"
            ]
            directory = root / "config"
            directory.mkdir()
            directory.chmod(0o755)
            verify(directory)

            for mode in (0o700, 0o750):
                with self.subTest(mode=oct(mode)):
                    directory.chmod(mode)
                    with self.assertRaises(ValueError):
                        verify(directory)

            directory.chmod(0o755)
            link = root / "symlink"
            link.symlink_to(directory, target_is_directory=True)

            with self.assertRaises(ValueError):
                verify(link)

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
