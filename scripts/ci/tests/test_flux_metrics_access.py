"""Security contracts for G3C Kubernetes and Flux metrics access."""

import copy
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "deploy/kubernetes/observability"

EXPECTED_SERVICES = {
    "flux-source-metrics": "source-controller",
    "flux-kustomize-metrics": "kustomize-controller",
}

EXPECTED_PROXY_NAMES = {
    "http:flux-source-metrics:metrics",
    "http:flux-kustomize-metrics:metrics",
}


def documents(filename):
    return list(
        yaml.safe_load_all(
            (BASE / filename).read_text()
        )
    )


def validate_services(items):
    if len(items) != 2:
        raise ValueError("Expected exactly two Services")

    services = {
        item["metadata"]["name"]: item
        for item in items
    }

    if set(services) != set(EXPECTED_SERVICES):
        raise ValueError("Unexpected metrics Service names")

    for name, controller in EXPECTED_SERVICES.items():
        item = services[name]
        metadata = item["metadata"]
        spec = item["spec"]

        if item["kind"] != "Service":
            raise ValueError("Unexpected resource kind")

        if metadata["namespace"] != "flux-system":
            raise ValueError("Service outside flux-system")

        if spec.get("type") != "ClusterIP":
            raise ValueError("Service not strictly ClusterIP")

        if spec.get("selector") != {"app": controller}:
            raise ValueError("Unsafe selector")

        if spec.get("ports") != [{
            "name": "metrics",
            "protocol": "TCP",
            "port": 8080,
            "targetPort": "http-prom",
        }]:
            raise ValueError("Unexpected Service ports")

        forbidden = {
            "externalIPs",
            "externalName",
            "loadBalancerIP",
            "loadBalancerSourceRanges",
            "externalTrafficPolicy",
        }

        if forbidden & set(spec):
            raise ValueError("Unsafe external exposure")


def validate_rbac(items):
    if len(items) != 4:
        raise ValueError("Expected exactly four RBAC resources")

    objects = {
        item["kind"]: item
        for item in items
    }

    expected_kinds = {
        "ClusterRole",
        "ClusterRoleBinding",
        "Role",
        "RoleBinding",
    }

    if set(objects) != expected_kinds:
        raise ValueError("Unexpected RBAC resource kinds")

    cluster = objects["ClusterRole"]

    if cluster["metadata"]["name"] != (
        "platform-observer-api-metrics"
    ):
        raise ValueError("Unexpected ClusterRole")

    if cluster["rules"] != [{
        "nonResourceURLs": ["/metrics"],
        "verbs": ["get"],
    }]:
        raise ValueError("Excessive API metrics permissions")

    role = objects["Role"]

    if role["metadata"] != {
        "name": "platform-observer-flux-metrics",
        "namespace": "flux-system",
    }:
        raise ValueError("Unexpected namespace Role identity")

    rules = role["rules"]

    if len(rules) != 1:
        raise ValueError("Unexpected number of proxy rules")

    rule = rules[0]

    if rule.get("apiGroups") != [""]:
        raise ValueError("Unexpected API group")

    if rule.get("resources") != ["services/proxy"]:
        raise ValueError("Unexpected proxy resource")

    if set(rule.get("resourceNames", [])) != EXPECTED_PROXY_NAMES:
        raise ValueError("Unexpected proxy targets")

    if len(rule.get("resourceNames", [])) != 2:
        raise ValueError("Duplicate or additional proxy target")

    if rule.get("verbs") != ["get"]:
        raise ValueError("Unexpected verbs")

    subject = [{
        "kind": "User",
        "name": "platform-observer",
        "apiGroup": "rbac.authorization.k8s.io",
    }]

    bindings = {
        "ClusterRoleBinding": (
            "platform-observer-api-metrics",
            "ClusterRole",
            "platform-observer-api-metrics",
        ),
        "RoleBinding": (
            "platform-observer-flux-metrics",
            "Role",
            "platform-observer-flux-metrics",
        ),
    }

    for kind, (name, ref_kind, ref_name) in bindings.items():
        binding = objects[kind]

        if binding["metadata"]["name"] != name:
            raise ValueError("Unexpected binding name")

        if binding["subjects"] != subject:
            raise ValueError("Unexpected monitoring subject")

        if binding["roleRef"] != {
            "apiGroup": "rbac.authorization.k8s.io",
            "kind": ref_kind,
            "name": ref_name,
        }:
            raise ValueError("Unexpected binding roleRef")

    if objects["RoleBinding"]["metadata"].get(
        "namespace"
    ) != "flux-system":
        raise ValueError("RoleBinding escaped namespace")


class FluxMetricsAccessTests(unittest.TestCase):

    def test_metrics_services(self):
        validate_services(
            documents("flux-metrics-services.yaml")
        )

    def test_exact_rbac(self):
        validate_rbac(
            documents("platform-observer-rbac.yaml")
        )

    def test_reject_exposed_services(self):
        original = documents("flux-metrics-services.yaml")

        mutations = [
            {"type": "NodePort"},
            {"type": "LoadBalancer"},
            {"externalIPs": ["10.0.0.50"]},
            {"selector": {"app": "anything"}},
            {"ports": [{
                "name": "admin",
                "port": 9090,
                "targetPort": "http",
            }]},
        ]

        for mutation in mutations:
            with self.subTest(mutation=mutation):
                bad = copy.deepcopy(original)
                bad[0]["spec"].update(mutation)

                with self.assertRaises(ValueError):
                    validate_services(bad)

    def test_reject_privilege_escalation(self):
        original = documents("platform-observer-rbac.yaml")

        mutations = [
            {"resources": ["secrets"]},
            {"resources": ["nodes/proxy"]},
            {"resources": ["pods/proxy"]},
            {"resourceNames": ["*"]},
            {"resourceNames": []},
            {"verbs": ["get", "create"]},
            {"verbs": ["*"]},
        ]

        for mutation in mutations:
            with self.subTest(mutation=mutation):
                bad = copy.deepcopy(original)
                bad[2]["rules"][0].update(mutation)

                with self.assertRaises(ValueError):
                    validate_rbac(bad)

    def test_reject_broader_api_metrics(self):
        original = documents("platform-observer-rbac.yaml")

        for urls in (["/*"], ["/metrics", "/debug/pprof/"]):
            with self.subTest(urls=urls):
                bad = copy.deepcopy(original)
                bad[0]["rules"][0]["nonResourceURLs"] = urls

                with self.assertRaises(ValueError):
                    validate_rbac(bad)

    def test_bootstrap_remains_outside_application_gitops(self):
        config = yaml.safe_load(
            (BASE / "kustomization.yaml").read_text()
        )

        self.assertEqual(
            set(config["resources"]),
            {
                "flux-metrics-services.yaml",
                "platform-observer-rbac.yaml",
            },
        )

        application = (
            ROOT / "clusters/home-pi/gitops/kustomization.yaml"
        ).read_text()

        self.assertNotIn("platform-observer", application)
        self.assertNotIn("flux-metrics-services", application)


if __name__ == "__main__":
    unittest.main()
