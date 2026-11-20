"""Protect the controller tunnel, private Forgejo boundary and credential handling."""

import importlib.util
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[3]
PROFILE = ROOT / "compose/caddy-public"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GUARD = load_module("public_guard", PROFILE / "check-storage.py")
INSTALLER = load_module("token_installer", ROOT / "scripts/cloudflared/install-token.py")


def rendered_project():
    project = yaml.safe_load((PROFILE / "compose.yaml").read_text())
    service = project["services"]["server"]
    service["environment"]["ZULIP_FQDN"] = "chat.example.com"
    service["environment"]["ZULIP_ORG_HOSTS"] = ""
    sources = {"/data": GUARD.STATE / "data", "/config": GUARD.STATE / "config",
               "/etc/caddy/Caddyfile": GUARD.COMPOSE / "Caddyfile"}
    for volume in service["volumes"]:
        volume["source"] = str(sources[volume["target"]])
    project["secrets"]["tunnel_token"]["file"] = str(GUARD.TOKEN)
    project["networks"]["tunnel"]["ipam"]["config"][0]["subnet"] = "192.0.2.0/28"
    service["networks"]["tunnel"]["ipv4_address"] = "192.0.2.3"
    service["environment"]["CLOUDFLARED_CONTAINER_IP"] = "192.0.2.2"
    project["services"]["cloudflared"]["networks"]["tunnel"]["ipv4_address"] = "192.0.2.2"
    return project


class PublicIngressTests(unittest.TestCase):
    def test_public_routes_exclude_forgejo_and_acme(self):
        config = (PROFILE / "Caddyfile").read_text()
        self.assertEqual(config.count("reverse_proxy "), 1)
        self.assertIn("@zulip host {$ZULIP_FQDN} {$ZULIP_ORG_HOSTS:}", config)
        self.assertIn("auto_https off", config)
        self.assertNotIn("forgejo", config.lower())
        self.assertNotIn("on_demand", config)
        self.assertNotIn("private_ranges", config)
        self.assertIn("client_ip_headers CF-Connecting-IP", config)
        self.assertIn("not remote_ip {$CLOUDFLARED_CONTAINER_IP}", config)
        self.assertIn("header_up X-Forwarded-Proto https", config)

    def test_neither_container_publishes_host_ports_or_has_host_privileges(self):
        config = rendered_project()
        for service in config["services"].values():
            self.assertFalse(service.get("ports"))
            self.assertNotIn("network_mode", service)
            self.assertNotIn("privileged", service)
            self.assertEqual(service["restart"], "no")
            self.assertEqual(service["cap_drop"], ["ALL"])
            self.assertTrue(service["read_only"])
        self.assertNotIn("platform_ingress", str(config))
        self.assertNotIn("docker.sock", str(config))
        self.assertTrue(config["networks"]["tunnel"]["internal"])
        self.assertEqual(set(config["services"]["server"]["networks"]) &
                         set(config["services"]["cloudflared"]["networks"]), {"tunnel"})

    def test_connector_uses_file_secret_nonroot_and_private_healthcheck(self):
        service = rendered_project()["services"]["cloudflared"]
        self.assertEqual(service["image"],
                         "cloudflare/cloudflared:2026.11.1@sha256:e613aadbc2d9511785d2e67a86b0c8ac18dd63a3f9af0d06faf04cbfdcb35f2d")
        self.assertEqual(service["user"], "65532:65532")
        self.assertEqual(service["secrets"], ["tunnel_token"])
        self.assertIn("--token-file", service["command"])
        self.assertNotIn("--token", service["command"])
        self.assertNotIn("environment", service)
        self.assertIn("127.0.0.1:2000", service["healthcheck"]["test"])
        self.assertIn("--management-diagnostics=false", service["command"])

    def test_app_override_excludes_old_local_caddy_and_limits_proxy_trust(self):
        config = yaml.safe_load((PROFILE / "zulip-upstream.override.yaml").read_text())["services"]
        self.assertTrue(config["caddy"]["profiles"])
        self.assertEqual(config["zulip"]["environment"]["LOADBALANCER_IPS"],
                         "${CONTROLLER_PROXY_IPV4:?Set CONTROLLER_PROXY_IPV4}")
        self.assertEqual(config["zulip"]["environment"]["TRUST_GATEWAY_IP"], "False")

    def test_lifecycle_waits_for_tunnel_and_prepares_without_auto_activation(self):
        unit = (PROFILE / "caddy-public.service").read_text()
        self.assertNotIn("forgejo.service", unit)
        self.assertIn("--wait --wait-timeout", unit)
        self.assertIn("ExecStopPost=-", unit)
        playbook = (ROOT / "ansible/playbooks/caddy-public.yml").read_text()
        self.assertIn("public_ingress_activate | default(false)", playbook)
        self.assertIn("cloudflared-install-token", playbook)


class ProjectGuardTests(unittest.TestCase):
    def test_accepts_isolated_tunnel_configuration(self):
        GUARD.validate_project(rendered_project())

    def test_accepts_explicit_organization_hosts(self):
        project = rendered_project()
        project["services"]["server"]["environment"]["ZULIP_ORG_HOSTS"] = (
            "openops.chat.example.com projects.chat.example.com")
        GUARD.validate_project(project)

    def test_rejects_wildcards_external_hosts_nested_hosts_and_duplicates(self):
        for hosts in ("*.chat.example.com", "projects.example.com", "chat.example.com",
                      "nested.openops.chat.example.com", "openops.chat.example.com:443",
                      "openops.chat.example.com openops.chat.example.com",
                      "openops.chat.example.com\nprojects.chat.example.com"):
            project = rendered_project()
            project["services"]["server"]["environment"]["ZULIP_ORG_HOSTS"] = hosts
            with self.subTest(hosts=hosts), self.assertRaisesRegex(SystemExit, "organization hostnames"):
                GUARD.validate_project(project)

    def test_rejects_invalid_base_hostname(self):
        for host in ("https://chat.example.com", "chat.example.com:443", "Chat.example.com",
                     "chat.example.com/path", "chat.example.com\nrespond bad"):
            project = rendered_project()
            project["services"]["server"]["environment"]["ZULIP_FQDN"] = host
            with self.subTest(host=host), self.assertRaisesRegex(SystemExit, "base hostname"):
                GUARD.validate_project(project)

    def test_rejects_host_port_publication(self):
        project = rendered_project()
        project["services"]["server"]["ports"] = ["443:443"]
        with self.assertRaisesRegex(SystemExit, "host ports"):
            GUARD.validate_project(project)

    def test_rejects_token_environment_and_argv(self):
        for change in ("environment", "command"):
            project = rendered_project()
            if change == "environment":
                project["services"]["cloudflared"][change] = {"TUNNEL_TOKEN": "test-only"}
            else:
                project["services"]["cloudflared"][change] = ["tunnel", "run", "--token", "test-only"]
            with self.subTest(change=change), self.assertRaisesRegex(SystemExit, "credentials"):
                GUARD.validate_project(project)

    def test_rejects_credential_source_outside_canonical_sd_path(self):
        project = rendered_project()
        project["secrets"]["tunnel_token"]["file"] = "/tmp/not-the-token"
        with self.assertRaisesRegex(SystemExit, "canonical SD"):
            GUARD.validate_project(project)

    def test_rejects_duplicate_proxy_addresses_and_wrong_trust(self):
        project = rendered_project()
        project["services"]["server"]["networks"]["tunnel"]["ipv4_address"] = "192.0.2.2"
        with self.assertRaisesRegex(SystemExit, "distinct"):
            GUARD.validate_project(project)
        project = rendered_project()
        project["services"]["server"]["environment"]["CLOUDFLARED_CONTAINER_IP"] = "192.0.2.4"
        with self.assertRaisesRegex(SystemExit, "exact tunnel"):
            GUARD.validate_project(project)

    def test_rejects_extra_persistent_mount(self):
        project = rendered_project()
        project["services"]["server"]["volumes"].append({"target": "/extra"})
        with self.assertRaisesRegex(SystemExit, "Unexpected persistent mounts"):
            GUARD.validate_project(project)

    def test_rejects_external_application_network(self):
        project = rendered_project()
        project["networks"]["tunnel"]["external"] = True
        with self.assertRaisesRegex(SystemExit, "external application networks"):
            GUARD.validate_project(project)


class TokenTests(unittest.TestCase):
    def test_installer_preserves_existing_token_and_rotates_only_explicitly(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "private/token"
            with patch.object(INSTALLER.os, "fchown"), patch.object(INSTALLER.os, "chown"):
                INSTALLER.store_token("test-only-first", path)
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o440)
                self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
                with self.assertRaises(FileExistsError):
                    INSTALLER.store_token("test-only-second", path)
                self.assertEqual(path.read_text(), "test-only-first")
                INSTALLER.store_token("test-only-second", path, replace=True)
                self.assertEqual(path.read_text(), "test-only-second")
                self.assertFalse(list(path.parent.glob(".tunnel-token-*")))

    def test_installer_rejects_invalid_input_and_redirected_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "token"
            for value in ("", "contains space", "line\nbreak", "null\x00byte"):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    INSTALLER.store_token(value, path)
            path.symlink_to(Path(directory) / "elsewhere")
            with self.assertRaises(ValueError):
                INSTALLER.store_token("test-only-value", path)

    def test_secret_guard_rejects_wrong_permissions_without_printing_value(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "token"
            path.write_text("test-only-sensitive-value")
            path.chmod(0o644)
            with self.assertRaisesRegex(SystemExit, "mode 0440") as caught:
                GUARD.validate_secret(path)
            self.assertNotIn("test-only-sensitive-value", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
