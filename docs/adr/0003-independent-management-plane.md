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
