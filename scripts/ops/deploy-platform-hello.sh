#!/usr/bin/env bash
set -Eeuo pipefail

# Deploy and verify platform-hello using caller-supplied Kubernetes credentials.
#
# This script intentionally does NOT:
#   - create the namespace;
#   - create or modify RBAC;
#   - create Kubernetes credentials;
#   - use SSH or kubeadm admin.conf;
#   - perform pods/exec or pods/portforward.
#
# Required:
#
#   KUBECONFIG=/path/to/scoped/config \
#     bash scripts/ops/deploy-platform-hello.sh
#
# Optional:
#
#   EXPECTED_KUBE_USER=platform-deployer

EXPECTED_KUBE_USER="${EXPECTED_KUBE_USER:-platform-deployer}"
NAMESPACE="platform-demo"
APP_NAME="platform-hello"
APP_LABEL="app.kubernetes.io/name=${APP_NAME}"

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

command -v kubectl >/dev/null 2>&1 ||
    fail "kubectl is required"

[[ -n "${KUBECONFIG:-}" ]] ||
    fail "KUBECONFIG must point to the scoped deployment kubeconfig"

[[ -f "$KUBECONFIG" ]] ||
    fail "KUBECONFIG does not exist: $KUBECONFIG"

REPO_ROOT="$(git rev-parse --show-toplevel)" ||
    fail "Not inside a Git repository"

cd "$REPO_ROOT"

DEPLOYMENT_MANIFEST="deploy/kubernetes/platform-hello/deployment.yaml"
SERVICE_MANIFEST="deploy/kubernetes/platform-hello/service.yaml"

[[ -f "$DEPLOYMENT_MANIFEST" ]] ||
    fail "Missing manifest: $DEPLOYMENT_MANIFEST"

[[ -f "$SERVICE_MANIFEST" ]] ||
    fail "Missing manifest: $SERVICE_MANIFEST"

KUBECTL=(
    kubectl
    --kubeconfig="$KUBECONFIG"
)

echo "=== KUBERNETES DEPLOYMENT PREFLIGHT ==="

WHOAMI_JSON="$("${KUBECTL[@]}" auth whoami -o json)" ||
    fail "Unable to determine Kubernetes identity"

ACTUAL_USER="$(
    python3 -c '
import json
import sys

print(json.load(sys.stdin)["status"]["userInfo"]["username"])
' <<<"$WHOAMI_JSON"
)" || fail "Unable to parse Kubernetes identity"

printf '%-20s %s\n' \
    "Expected user:" "$EXPECTED_KUBE_USER" \
    "Authenticated user:" "$ACTUAL_USER"

[[ "$ACTUAL_USER" == "$EXPECTED_KUBE_USER" ]] ||
    fail "Refusing deployment with unexpected Kubernetes identity"

for permission in \
    "get deployments.apps" \
    "create deployments.apps" \
    "patch deployments.apps" \
    "get services" \
    "create services" \
    "patch services" \
    "get pods" \
    "get replicasets.apps" \
    "get endpointslices.discovery.k8s.io"
do
    verb="${permission%% *}"
    resource="${permission#* }"

    allowed="$(
        "${KUBECTL[@]}" auth can-i \
            "$verb" "$resource" \
            -n "$NAMESPACE"
    )"

    [[ "$allowed" == "yes" ]] ||
        fail "Required permission denied: $verb $resource"
done

EXPECTED_IMAGE="$(
    "${KUBECTL[@]}" create \
        --dry-run=client \
        -f "$DEPLOYMENT_MANIFEST" \
        -o jsonpath='{.spec.template.spec.containers[0].image}'
)" || fail "Unable to read desired image from Deployment manifest"

[[ "$EXPECTED_IMAGE" == *@sha256:* ]] ||
    fail "Deployment image is not pinned by sha256 digest: $EXPECTED_IMAGE"

EXPECTED_DIGEST="${EXPECTED_IMAGE##*@}"

echo
echo "=== RECONCILE DESIRED STATE ==="

"${KUBECTL[@]}" apply \
    -f "$DEPLOYMENT_MANIFEST" \
    -f "$SERVICE_MANIFEST"

echo
echo "=== VERIFY ROLLOUT ==="

"${KUBECTL[@]}" rollout status \
    "deployment/$APP_NAME" \
    -n "$NAMESPACE" \
    --timeout=120s

"${KUBECTL[@]}" wait \
    --for=condition=Ready \
    pod \
    -l "$APP_LABEL" \
    -n "$NAMESPACE" \
    --timeout=60s

POD="$(
    "${KUBECTL[@]}" get pods \
        -n "$NAMESPACE" \
        -l "$APP_LABEL" \
        --field-selector=status.phase=Running \
        -o jsonpath='{.items[0].metadata.name}'
)" || fail "Unable to resolve running application Pod"

[[ -n "$POD" ]] ||
    fail "No running platform-hello Pod found"

RUNTIME_IMAGE="$(
    "${KUBECTL[@]}" get pod "$POD" \
        -n "$NAMESPACE" \
        -o jsonpath='{.status.containerStatuses[0].imageID}'
)" || fail "Unable to read runtime image identity"

RUNTIME_DIGEST="${RUNTIME_IMAGE##*@}"

printf '%-20s %s\n' \
    "Pod:" "$POD" \
    "Desired image:" "$EXPECTED_IMAGE" \
    "Expected digest:" "$EXPECTED_DIGEST" \
    "Runtime image:" "$RUNTIME_IMAGE" \
    "Runtime digest:" "$RUNTIME_DIGEST"

[[ "$RUNTIME_DIGEST" == "$EXPECTED_DIGEST" ]] ||
    fail "Runtime digest does not match desired digest"

ENDPOINTS="$(
    "${KUBECTL[@]}" get endpointslice \
        -n "$NAMESPACE" \
        -l "kubernetes.io/service-name=$APP_NAME" \
        -o jsonpath='{range .items[*].endpoints[*]}{.addresses[0]}{"\n"}{end}'
)" || fail "Unable to inspect Service EndpointSlice"

[[ -n "$ENDPOINTS" ]] ||
    fail "Service has no EndpointSlice addresses"

echo
echo "=== SERVICE ENDPOINTS ==="
printf '%s\n' "$ENDPOINTS"

echo
echo "PASS: scoped Kubernetes deployment and runtime verification completed."
