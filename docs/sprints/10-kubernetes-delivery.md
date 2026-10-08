# Sprint 10 — Kubernetes Delivery

**Work item:** PLAT-009
**Completed:** 2026-10-08
**Status:** Complete — digest-pinned Kubernetes delivery with scoped external deployment identity proven
**Application:** `platform-hello`

## Objective

Extend the verified OCI delivery chain into the existing Raspberry Pi kubeadm
cluster without rebuilding the qualified application artifact.

The sprint must prove:

1. the CI-qualified artifact can be deployed by immutable registry digest;
2. Kubernetes runs the expected artifact identity;
3. rollout and application networking succeed;
4. workload manifests remain independent of individual node names and cluster
   topology;
5. routine deployment does not require SSH to a control-plane host or
   cluster-admin credentials;
6. the external deployment identity is constrained by namespace-scoped RBAC;
7. deployment and verification are reproducible through repository-owned
   tooling.

## Cluster discovery

The existing kubeadm cluster runs Kubernetes `v1.34.11` on ARM64.

Topology at the time of PLAT-009:

```text
ci-controller-01.lab.home.arpa
  control plane
  10.0.0.5

ci-controller-02.lab.home.arpa
  worker
  10.0.0.6

ci-controller-04.lab.home.arpa
  worker
  10.0.0.8
```

The cluster uses containerd and Flannel.

The application manifests intentionally contain no node names, worker-count
assumptions, node IPs, CNI-specific configuration, host networking, NodePort,
Ingress, or persistent-storage requirements.

## Control-plane recovery discovered during delivery work

Initial cluster inspection exposed stale higher-level controller state even
though existing Pods remained running.

The `kube-controller-manager` static Pod could not restart because containerd
held a stale CRI Pod sandbox reservation.

The stale sandbox was identified through CRI inspection and removed
surgically. Kubelet then recreated the static Pod automatically.

After recovery:

```text
kube-controller-manager   1/1 Running
nginx-test                6/6
web-svc-test              3/3
coredns                   2/2
flannel                   3/3
kube-proxy                3/3
```

This demonstrated the distinction between:

- kubelets maintaining already-scheduled Pods locally; and
- higher-level Kubernetes controllers reconciling Deployment and ReplicaSet
  desired state.

The control-plane role label and `NoSchedule` taint were also restored before
new application scheduling.

## Workload definition

PLAT-009 added raw Kubernetes manifests under:

```text
deploy/kubernetes/platform-hello/
```

Resources:

- Namespace `platform-demo`;
- Deployment `platform-hello`;
- ClusterIP Service `platform-hello`.

The Deployment runs one replica of:

```text
ghcr.io/ctalaveraw/platform-hello@sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e
```

The image reference is pinned by immutable registry digest.

`imagePullPolicy: IfNotPresent` is explicit and documented in ADR-0007.

The container:

- runs as UID/GID `10001`;
- requires a non-root runtime;
- disables privilege escalation;
- drops all Linux capabilities;
- exposes application port `8080`;
- has an HTTP readiness probe.

## First-pull proof

Before the first Deployment was created, both schedulable worker nodes were
inspected through containerd.

Neither worker contained `platform-hello`.

Kubernetes then scheduled the new Pod onto:

```text
home-phy-srv-deb-ci-controller-04
```

After rollout, that worker contained:

```text
ghcr.io/ctalaveraw/platform-hello@sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e
```

with the expected Linux ARM64 manifest digest.

Because the artifact was absent from both eligible workers before scheduling,
the first deployment proves a real registry retrieval rather than reuse of a
pre-existing local application cache.

## Runtime artifact identity

The Deployment declared:

```text
sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e
```

The running container reported:

```text
sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e
```

The scheduled worker's containerd image inventory reported the same digest.

This extends the build-once artifact identity chain from CI and registry
distribution into the running Kubernetes workload.

## Service and application verification

The ClusterIP Service received:

```text
10.101.39.146
```

Its EndpointSlice pointed to the Ready Pod:

```text
10.244.3.9:8080
```

An in-cluster request through Kubernetes Service DNS:

```text
http://platform-hello.platform-demo.svc.cluster.local/
```

returned HTTP 200 and the expected application content.

A temporary `kubectl port-forward` test also returned the expected application
response during initial acceptance.

The Service-DNS test provides the stronger proof of the normal in-cluster
ClusterIP data path.

## Management-controller Kubernetes client baseline

The independent NanoPi R5C did not initially contain `kubectl`.

A dedicated Ansible `kubernetes_client` role now:

- installs version-pinned `kubectl v1.34.11` for Linux ARM64;
- installs it at `/usr/local/bin/kubectl`;
- creates `/home/runner/.kube` with mode `0700`;
- verifies the installed client version.

The first convergence installed the capability.

The second convergence reported:

```text
changed=0
failed=0
```

The ordinary management-host baseline manages Kubernetes client tooling but
does not issue or embed cluster credentials.

## Namespace-scoped authorization

PLAT-009 added:

```text
deploy/kubernetes/access/platform-demo-deployer.yaml
```

with a `Role` and `RoleBinding` for Kubernetes user:

```text
platform-deployer
```

The identity may create/update/patch Deployments and Services in
`platform-demo` and read the runtime resources required to verify rollout.

Negative authorization tests proved it cannot:

- create namespaces;
- deploy into `default`;
- read Secrets;
- mutate RoleBindings;
- read Nodes;
- delete the Deployment;
- create Pods directly;
- use `pods/exec`.

The authorization matrix was tested first through Kubernetes impersonation and
then repeated using the real external credential.

## External X.509 deployment identity

The R5C generated its own private key and PKCS#10 certificate request.

The private key never left the R5C.

The Kubernetes CSR API received a request with:

```text
CN=platform-deployer
signer=kubernetes.io/kube-apiserver-client
usage=client auth
requested duration=90d
```

The request was explicitly approved and issued.

The resulting certificate:

- validates against the Kubernetes cluster CA;
- authenticates as `platform-deployer`;
- belongs only to `system:authenticated`;
- is stored as host-local security material outside Git.

No kubeadm `admin.conf` was copied to the R5C.

ADR-0008 records the authentication and authorization decision.

## Direct deployment without SSH

The R5C successfully connected directly to:

```text
https://10.0.0.5:6443
```

with the scoped X.509 identity.

Applying the repository manifests returned:

```text
deployment.apps/platform-hello unchanged
service/platform-hello unchanged
```

The Deployment then reported a successful rollout.

This proves that routine application reconciliation no longer requires the
bootstrap path:

```text
R5C -> SSH -> control-plane -> kubernetes-admin
```

## Repository-owned deployment interface

PLAT-009 added:

```text
scripts/ops/deploy-platform-hello.sh
```

The script requires caller-supplied Kubernetes credentials.

It:

1. verifies the authenticated Kubernetes username;
2. checks required RBAC permissions;
3. extracts the desired digest from the repository Deployment manifest;
4. refuses a non-digest image reference;
5. reconciles the Deployment and Service;
6. waits for successful rollout and Pod readiness;
7. compares runtime image digest with desired digest;
8. verifies that the Service has EndpointSlice addresses.

The script does not:

- create the Namespace;
- modify RBAC;
- issue credentials;
- use SSH;
- use kubeadm administrator credentials;
- require `pods/exec` or `pods/portforward`.

Final execution reported:

```text
Expected user:       platform-deployer
Authenticated user:  platform-deployer

deployment.apps/platform-hello unchanged
service/platform-hello unchanged

deployment "platform-hello" successfully rolled out
pod/platform-hello-57999d5984-pws46 condition met

Expected digest:
sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e

Runtime digest:
sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e

PASS: scoped Kubernetes deployment and runtime verification completed.
```

## Credential lifecycle

The first external credential was deliberately bootstrapped manually so the
authentication and authorization model could be understood and proven before
automation.

The scoped X.509 path remains suitable for independent bootstrap and recovery.

PLAT-016 will evaluate OpenBao dynamic Kubernetes credentials for normal
operation so short-lived routine credentials can be issued without making
OpenBao a prerequisite for management-plane bootstrap.

Certificate-lifecycle automation is therefore not a blocker for PLAT-009.

## Validation

Repository validation passed after the Kubernetes manifests were tracked.

Validation included:

- Bash syntax;
- ShellCheck;
- Python parsing;
- Ruff;
- YAML parsing;
- yamllint;
- actionlint;
- Compose safety-contract tests;
- Ansible playbook syntax;
- Compose rendering.

The Kubernetes client Ansible role also proved runtime idempotence with a
second `changed=0` convergence.

## Acceptance

PLAT-009 acceptance criteria:

- [x] deploy CI-produced image into Kubernetes by immutable digest;
- [x] prove first worker retrieval of the artifact;
- [x] verify running image identity matches the published digest;
- [x] verify Deployment rollout;
- [x] verify Ready Pod;
- [x] verify ClusterIP Service and EndpointSlice;
- [x] verify application response through in-cluster Service DNS;
- [x] keep workload manifests independent of concrete worker names;
- [x] establish namespace-scoped deployment authorization;
- [x] prove negative authorization boundaries;
- [x] establish direct external authentication without kubeadm `admin.conf`;
- [x] remove SSH and cluster-admin from routine application reconciliation;
- [x] provide repository-owned deployment and verification tooling;
- [x] pass repository validation.

**PLAT-009 functional acceptance: PASSED.**

## Next sprint — PLAT-010

Perform a controlled Kubernetes deployment failure and rollback/recovery
exercise.

The next milestone must demonstrate not merely successful deployment, but how
the platform behaves when a deployment is intentionally broken.
