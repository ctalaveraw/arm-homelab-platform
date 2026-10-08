# ADR-0003: Independent Management Plane and Recovery Source

Status: Accepted
Recorded: 2026-10-04 (retrospective)

## Context

The homelab has an existing upstream kubeadm Kubernetes cluster.
A separate NanoPi R5C operates the management services.

Placing foundational delivery services inside the cluster
would introduce bootstrap and recovery dependencies.

## Decision

- Keep the R5C management plane outside Kubernetes.
- Host Gitea and supporting services independently.
- Keep the public GitHub repository as an external
  bootstrap and recovery source.
- Do not require the self-hosted Gitea instance to
  reconstruct the management plane.
- Preserve local host-specific secrets outside public Git.

## Consequences

Management tooling remains available during many
compute-plane failures.

The R5C is nevertheless a shared failure domain and
does not provide high availability.

Fresh-host reconstruction and off-device application
restore remain separate, unverified acceptance criteria.

## Implementation update — 2026-10-04

Gitea now has a native, private pull mirror of this public GitHub repository.
GitHub remains the upstream source of truth; no bidirectional or dual-push
workflow is configured. GitHub-hosted ARM64 CI works independently of the
R5C and Gitea.

A repository-scoped Gitea Actions runner now runs on the R5C while GitHub-hosted ARM64 Actions continues to operate independently.

This preserves the original recovery decision:

- GitHub can validate/build without the R5C.
- Gitea can validate mirrored source inside the homelab.
- The Gitea runner has no production Docker socket and no deployment credentials.
- Application artifact publication is designed so external distribution and local distribution remain separate from source ownership.

## Implementation update — 2026-10-05

The controller working copy now has two intentionally asymmetric remotes:

- GitHub: fetch + normal push destination;
- Gitea: fetch-only mirror inspection.

`scripts/ops/check-source-parity.sh` fetches both and compares local `main`, GitHub `main`, and Gitea `main`.

This makes source convergence measurable without promoting Gitea into a second source of truth.

GitHub `main` is protected and the external GHCR publication path now operates independently of Gitea. Loss of the self-hosted management plane therefore does not remove the canonical source repository or the externally published application artifact.

## Implementation update — 2026-10-07

PLAT-009 extends the independent R5C management controller with an
Ansible-managed Kubernetes client capability.

The management baseline now includes a dedicated `kubernetes_client` role that:

- installs a version-pinned `kubectl` client for Linux ARM64;
- currently pins `kubectl` to `v1.34.11`, matching the Kubernetes API server
  version used during PLAT-009;
- installs the client at `/usr/local/bin/kubectl`;
- creates `/home/runner/.kube` with `runner:runner` ownership and mode `0700`;
- verifies the installed client version during convergence.

The role intentionally manages client tooling and protected configuration
scaffolding only.

It does not manage:

- kubeadm `admin.conf`;
- Kubernetes client certificates or private keys;
- ServiceAccount tokens;
- cluster-admin credentials;
- host-local deployment credentials.

This preserves the recovery boundary established by this ADR: the R5C can be
reconstructed with the tooling required to act as an external Kubernetes
management client without embedding cluster credentials in the public
repository or copying the kubeadm administrator identity onto the management
host.

The first convergence installed `kubectl` and created the protected
configuration directory. A second convergence completed with `changed=0`,
proving the Kubernetes client baseline is idempotently Ansible-owned.

PLAT-009 will establish a separately scoped deployment identity for direct
R5C-to-Kubernetes API access. The authentication mechanism and associated
least-privilege policy are evaluated separately from this management-plane
bootstrap decision.
