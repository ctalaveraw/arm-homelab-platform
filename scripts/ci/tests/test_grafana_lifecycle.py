"""Portable Grafana lifecycle and fail-closed contracts."""

import copy
import runpy
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[3]
OBS = ROOT / "compose/observability"


def check_policy(service):
    expected = {
        "restart": "no",
        "user": "472:472",
        "read_only": True,
        "mem_limit": "512m",
        "pids_limit": 256,
        "cap_drop": ["ALL"],
        "security_opt": ["no-new-privileges:true"],
        "ports": ["10.0.0.50:3300:3000"],
    }
    for field, value in expected.items():
        if service.get(field) != value:
            raise ValueError(f"Unsafe Grafana setting: {field}")

    if service.get("privileged") is True:
        raise ValueError("Privileged container")

    if service.get("network_mode") == "host":
        raise ValueError("Host networking")

    env = service.get("environment", {})
    if (
        env.get("GF_SECURITY_ADMIN_PASSWORD__FILE")
        != "/run/secrets/grafana-admin-password"
        or "GF_SECURITY_ADMIN_PASSWORD" in env
        or env.get("GF_PLUGINS_PREINSTALL_AUTO_UPDATE") != "false"
    ):
        raise ValueError("Unsafe bootstrap or plugin update configuration")

    sources = {
        "/var/lib/grafana": (
            "${STATE_SERVICES_ROOT:?Set STATE_SERVICES_ROOT}/grafana",
            False,
        ),
        "/run/secrets/grafana-admin-password": (
            "${STATE_SERVICES_ROOT:?Set STATE_SERVICES_ROOT}/grafana-auth/admin-password",
            True,
        ),
        "/etc/grafana/provisioning": ("./grafana/provisioning", True),
        "/etc/grafana/dashboards": ("./grafana/dashboards", True),
    }

    volumes = service.get("volumes", [])
    if len(volumes) != len(sources):
        raise ValueError("Wrong mount count")

    found = set()
    for volume in volumes:
        target = volume.get("target")
        if target in found or target not in sources:
            raise ValueError("Unexpected mount")
        found.add(target)
        source, readonly = sources[target]
        if (
            volume.get("type") != "bind"
            or volume.get("source") != source
            or volume.get("read_only", False) is not readonly
            or volume.get("bind", {}).get("create_host_path") is not False
        ):
            raise ValueError(f"Unsafe bind: {target}")


class GrafanaLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.service = yaml.safe_load(
            (OBS / "compose.yml").read_text()
        )["services"]["grafana"]

    def test_policy_and_mutation_rejection(self):
        check_policy(self.service)

        for field, value in (
            ("restart", "always"),
            ("user", "0:0"),
            ("read_only", False),
            ("mem_limit", None),
            ("ports", ["0.0.0.0:3300:3000"]),
        ):
            with self.subTest(field=field):
                bad = copy.deepcopy(self.service)
                bad[field] = value
                with self.assertRaises(ValueError):
                    check_policy(bad)

        for target in (
            "/var/lib/grafana",
            "/run/secrets/grafana-admin-password",
        ):
            with self.subTest(target=target):
                bad = copy.deepcopy(self.service)
                volume = next(
                    v for v in bad["volumes"] if v["target"] == target
                )
                volume["bind"]["create_host_path"] = True
                with self.assertRaises(ValueError):
                    check_policy(bad)

    def test_auto_update_is_rejected(self):
        bad = copy.deepcopy(self.service)
        bad["environment"]["GF_PLUGINS_PREINSTALL_AUTO_UPDATE"] = "true"

        with self.assertRaises(ValueError):
            check_policy(bad)

    def test_unit_and_ansible_integration(self):
        unit = (OBS / "grafana.service").read_text()
        self.assertIn(
            "ExecStartPre=/usr/local/sbin/grafana-check-storage", unit
        )
        self.assertIn(" up -d grafana", unit)
        self.assertIn(" stop grafana", unit)
        self.assertIn("RequiresMountsFor=", unit)

        playbook = yaml.safe_load(
            (ROOT / "ansible/playbooks/08-grafana.yml").read_text()
        )
        self.assertEqual(
            playbook[0]["import_playbook"], "00-preflight.yml"
        )
        tasks = playbook[1]["tasks"]
        self.assertEqual(
            [
                task["ansible.builtin.uri"]["url"]
                for task in tasks
                if "ansible.builtin.uri" in task
            ],
            ["http://10.0.0.50:3300/api/health"],
        )
        self.assertTrue(
            any(
                task.get("ansible.builtin.command", {}).get("creates")
                == "/srv/storage/state/services/grafana-auth/admin-password"
                for task in tasks
            )
        )

    def test_inaccessible_sd_fails_closed(self):
        def deny_ls(argv, **kwargs):
            self.assertEqual(argv[0], "/usr/bin/ls")
            return subprocess.CompletedProcess(
                argv, 1, stdout="", stderr=""
            )

        with (
            patch("subprocess.run", side_effect=deny_ls),
            self.assertRaises(SystemExit) as caught,
        ):
            runpy.run_path(
                str(OBS / "grafana-check-storage.py"),
                run_name="__main__",
            )

        self.assertIn(
            "Grafana storage preflight FAILED",
            str(caught.exception),
        )


if __name__ == "__main__":
    unittest.main()
