# ADR-0003: Independent management and recovery source

Status: Accepted
Recorded: 2026-10-04

## Context

The homelab has a three-node kubeadm cluster and a separate R5C management host. Hosting its only source, credentials or management tools inside that cluster would complicate bootstrap and recovery.

## Decision

Keep the R5C outside Kubernetes. GitHub owns canonical source and external CI/publication. Forgejo provides a local one-way pull mirror, restricted validation and OCI distribution.

Recovery must be possible with the local forge or cluster unavailable. Keep protected host/cluster credentials and off-device backups accessible independently.

## Implementation

The controller checkout uses canonical remote `github` and fetch-only remote `forgejo`. `scripts/ops/check-source-parity.sh github forgejo` compares local and both remote main branches. Forgejo parity and native validation passed after the 2026-11-18 migration.

GitHub ARM64 CI builds, tests and scans the application, then publishes to GHCR. Kubernetes and Flux read GitHub/GHCR directly. Forgejo's runner has no production Docker socket or deployment credentials.

Ansible's `kubernetes_client` role installs pinned ARM64 kubectl and protected configuration directories. The `flux_client` role installs the Flux CLI. Credentials are supplied separately; public source contains no kubeadm administrator configuration or client private keys.

The original Gitea implementation is documented in the [dated sprint records](../sprints/06-ci-foundation.md). [ADR-0015](0015-forgejo-and-controller-ingress.md) records the replacement.

## Consequences

Management tools remain available during many cluster failures. The R5C is still one host and provides no high availability.

Fresh-host reconstruction and full application restore remain untested. Source convergence and an external image copy cover only part of recovery.
