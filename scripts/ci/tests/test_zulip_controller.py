"""Guard the colocated app's storage, proxy trust and credential preservation."""

import copy
import json
import re
import stat
import tempfile
import unittest
from pathlib import Path

import yaml
from test_controller_public_ingress import GUARD, ROOT, load_module, rendered_project

INSTALLER = load_module("zulip_installer", ROOT / "scripts/zulip/init-secrets.py")


def colocated_project():
    project = rendered_project()
    overlay = yaml.safe_load((ROOT / "compose/zulip/compose.yaml").read_text())
    for name, service in overlay["services"].items():
        if name not in project["services"]:
            project["services"][name] = copy.deepcopy(service)
        else:
            for key, value in service.items():
                project["services"][name].setdefault(key, {}).update(value)
    project["networks"].update(overlay["networks"])
    project["secrets"].update(overlay["secrets"])
    values = {
        "STATE_SERVICES_ROOT": str(GUARD.MOUNT / "services"),
        "ZULIP_FQDN": "chat.example.com", "ZULIP_ADMIN_EMAIL": "admin@example.com",
        "ZULIP_REALM_HOSTS": "",
        "SMTP_HOST": "smtp.example.com", "SMTP_USER": "test@example.com", "SMTP_FROM": "test@example.com",
        "CADDY_ZULIP_IP": "198.51.100.2", "ZULIP_CONTAINER_IP": "198.51.100.3",
        "ZULIP_PROXY_SUBNET": "198.51.100.0/28",
    }

    def interpolate(value):
        if isinstance(value, dict):
            return {key: interpolate(item) for key, item in value.items()}
        if isinstance(value, list):
            return [interpolate(item) for item in value]
        if isinstance(value, str):
            return re.sub(r"\$\{(\w+)(?::[^}]*)?\}", lambda match: values.get(match[1], match[0]), value)
        return value

    project = interpolate(project)
    for service in project["services"].values():
        if isinstance(service.get("networks"), list):
            service["networks"] = {name: {} for name in service["networks"]}
    return project


class ColocatedZulipTests(unittest.TestCase):
    def test_accepts_mapped_sibling_hosts_and_default_nested_hosts(self):
        project = colocated_project()
        server = project["services"]["server"]["environment"]
        environment = project["services"]["zulip"]["environment"]
        mapping = {"openops": "zulip-openops.example.com", "projects": "zulip-projects.example.com"}
        server["ZULIP_ORG_HOSTS"] = " ".join(mapping.values())
        environment["SETTING_REALM_HOSTS"] = json.dumps(mapping)
        GUARD.validate_project(project)
        server["ZULIP_ORG_HOSTS"] = "openops.chat.example.com projects.chat.example.com"
        environment["SETTING_REALM_HOSTS"] = ""
        GUARD.validate_project(project)

    def test_rejects_missing_mismatched_and_duplicate_realm_destinations(self):
        for mapping in ({}, {"openops": "zulip-openops.example.com"},
                        {"openops": "unlisted.example.com", "projects": "zulip-projects.example.com"},
                        {"openops": "zulip-openops.example.com", "projects": "zulip-openops.example.com"}):
            project = colocated_project()
            project["services"]["server"]["environment"]["ZULIP_ORG_HOSTS"] = (
                "zulip-openops.example.com zulip-projects.example.com")
            project["services"]["zulip"]["environment"]["SETTING_REALM_HOSTS"] = json.dumps(mapping)
            with self.subTest(mapping=mapping), self.assertRaisesRegex(SystemExit, "REALM_HOSTS"):
                GUARD.validate_project(project)

    def test_rejects_invalid_realm_mapping_input(self):
        for raw in ("not JSON", "[]", '{"": "zulip-openops.example.com"}',
                    '{"zulipinternal": "zulip-openops.example.com"}', '{"openops": 42}',
                    '{"OpenOps": "zulip-openops.example.com"}'):
            project = colocated_project()
            project["services"]["server"]["environment"]["ZULIP_ORG_HOSTS"] = "zulip-openops.example.com"
            project["services"]["zulip"]["environment"]["SETTING_REALM_HOSTS"] = raw
            with self.subTest(raw=raw), self.assertRaisesRegex(SystemExit, "REALM_HOSTS"):
                GUARD.validate_project(project)

    def test_rejects_a_second_route_or_mapping_that_shadows_a_natural_subdomain(self):
        for hosts, mapping in (
                ("openops.chat.example.com zulip-openops.example.com", {"openops": "zulip-openops.example.com"}),
                ("projects.chat.example.com", {"openops": "projects.chat.example.com"})):
            project = colocated_project()
            project["services"]["server"]["environment"]["ZULIP_ORG_HOSTS"] = hosts
            project["services"]["zulip"]["environment"]["SETTING_REALM_HOSTS"] = json.dumps(mapping)
            with self.subTest(hosts=hosts), self.assertRaisesRegex(SystemExit, "REALM_HOSTS"):
                GUARD.validate_project(project)

    def test_accepts_compose_v2_omitted_false_in_explicit_bind_object(self):
        project = colocated_project()
        for service in project["services"].values():
            for volume in service.get("volumes", []):
                volume["bind"] = {}
        GUARD.validate_project(project)

    def test_rejects_automatic_or_unspecified_bind_path_creation(self):
        for bind in (None, {"create_host_path": True}):
            project = colocated_project()
            volume = project["services"]["zulip"]["volumes"][0]
            if bind is None:
                del volume["bind"]
            else:
                volume["bind"] = bind
            with self.subTest(bind=bind), self.assertRaisesRegex(SystemExit, "SD storage"):
                GUARD.validate_project(project)

    def test_accepts_private_colocated_project_without_host_listeners(self):
        project = colocated_project()
        GUARD.validate_project(project)
        self.assertEqual(len(project["services"]), 7)
        self.assertTrue(project["networks"]["zulip_proxy"]["internal"])
        self.assertFalse(set(project["services"]["cloudflared"]["networks"]) &
                         set(project["services"]["zulip"]["networks"]))
        for service in project["services"].values():
            self.assertFalse(service.get("ports"))
            self.assertEqual(service["restart"], "no")
        self.assertEqual(project["services"]["zulip"]["mem_limit"], "1536m")

    def test_rejects_publication_and_dependency_access_from_ingress(self):
        project = colocated_project()
        project["services"]["zulip"]["ports"] = ["80:80"]
        with self.assertRaisesRegex(SystemExit, "host ports"):
            GUARD.validate_project(project)
        project = colocated_project()
        project["services"]["database"]["networks"]["zulip_proxy"] = {}
        with self.assertRaisesRegex(SystemExit, "isolation"):
            GUARD.validate_project(project)

    def test_rejects_gateway_trust_and_wrong_caddy_peer(self):
        for key, value in (("TRUST_GATEWAY_IP", "True"), ("LOADBALANCER_IPS", "198.51.100.0/24")):
            project = colocated_project()
            project["services"]["zulip"]["environment"][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(SystemExit, "exact Caddy"):
                GUARD.validate_project(project)

    def test_rejects_shared_subnet_and_duplicate_static_peers(self):
        project = colocated_project()
        project["networks"]["zulip_proxy"]["ipam"]["config"][0]["subnet"] = "192.0.2.0/24"
        with self.assertRaisesRegex(SystemExit, "separate internal subnet"):
            GUARD.validate_project(project)
        project = colocated_project()
        project["services"]["zulip"]["networks"]["zulip_proxy"]["ipv4_address"] = "198.51.100.2"
        with self.assertRaisesRegex(SystemExit, "separate internal subnet"):
            GUARD.validate_project(project)

    def test_rejects_wrong_bind_and_relocated_credentials(self):
        project = colocated_project()
        project["services"]["database"]["volumes"][0]["source"] = "/tmp/database"
        with self.assertRaisesRegex(SystemExit, "SD storage"):
            GUARD.validate_project(project)
        project = colocated_project()
        project["secrets"]["zulip__secret_key"]["file"] = "/tmp/secrets"
        with self.assertRaisesRegex(SystemExit, "canonical SD"):
            GUARD.validate_project(project)

    def test_cold_start_rejects_insufficient_memory_swap_or_storage(self):
        memory = {"MemTotal": 4 * 1024**2, "SwapTotal": 2 * 1024**2, "MemAvailable": 2 * 1024**2}
        GUARD.validate_capacity(memory, 20 * 1024**3)
        for key in memory:
            insufficient = memory | {key: 0}
            with self.subTest(key=key), self.assertRaises(SystemExit):
                GUARD.validate_capacity(insufficient, 20 * 1024**3)
        with self.assertRaisesRegex(SystemExit, "10 GiB"):
            GUARD.validate_capacity(memory, 1024**3)


class CredentialTests(unittest.TestCase):
    def test_complete_set_is_preserved_on_reinitialization(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / "secrets"
            INSTALLER.store_secrets("test-only-smtp-password", folder)
            original = {name: (folder / name).read_bytes() for name in INSTALLER.NAMES}
            self.assertEqual({path.name for path in folder.iterdir()}, set(INSTALLER.NAMES))
            self.assertEqual(stat.S_IMODE(folder.stat().st_mode), 0o700)
            self.assertTrue(all(stat.S_IMODE(path.stat().st_mode) == 0o444 for path in folder.iterdir()))
            with self.assertRaises(FileExistsError):
                INSTALLER.store_secrets("test-only-replacement", folder)
            self.assertEqual(original, {name: (folder / name).read_bytes() for name in INSTALLER.NAMES})
            self.assertFalse(list(Path(directory).glob(".secrets-*")))

    def test_rejects_invalid_input_and_redirected_storage(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / "secrets"
            for value in ("", "line\nbreak", "null\x00byte"):
                with self.assertRaises(ValueError):
                    INSTALLER.store_secrets(value, folder)
                self.assertFalse(folder.exists())
            folder.symlink_to(Path(directory) / "elsewhere")
            with self.assertRaises(ValueError):
                INSTALLER.store_secrets("test-only-password", folder)


if __name__ == "__main__":
    unittest.main()
