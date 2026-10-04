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
The mirror displayed the canonical `main` commit `3e58f61` following
synchronization. GitHub remains the upstream source of truth; no
bidirectional or dual-push workflow is configured. GitHub-hosted ARM64
CI works independently of the R5C and Gitea.
