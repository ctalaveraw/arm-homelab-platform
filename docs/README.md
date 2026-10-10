# Documentation Index

This directory separates **current-state documentation** from **historical evidence**. Historical sprint, incident, and benchmark records are intentionally not rewritten to pretend later capabilities existed at the time.

## Current state

- [Architecture overview](architecture/overview.md) — current implemented and planned component relationships.
- [Roadmap](roadmap.md) — milestone-level progress toward application delivery.
- [Backlog](backlog.md) — active and queued work items.
- [CI, mirroring and OCI publication](ci.md) — GitHub/Gitea CI behavior, validation contracts, artifact handoff, and GHCR publication.
- [Engineering evidence ledger](interview/engineering-evidence.md) — interview-oriented proof of implementation and verification.
- [R5C baseline](architecture/r5c-baseline.md) — original brownfield snapshot plus a current-state delta.

## Target vision and planning (not yet implemented)

- [Platform charter](vision/platform-charter.md) — ARM-first portable DevSecOps purpose, owners, trust boundaries, success criteria and recovery targets.
- [Full objective register](planning/objectives.md) — 93 testable planned/evaluate-only objectives across all platform streams.
- [Approved decisions and open implementation gates](planning/design-gates.md) — eight approved choices and questions that must be resolved before live activation.
- [Phased roadmap](roadmap.md) — PLAT-012..018 sequencing followed by security, trusted operations, portability and documentation.
- [Active backlog](backlog.md) — historical progress plus every additional tracked objective; proposed controls are not marked complete.

## Architecture decisions

- [ADR-0001 — Management plane storage layout](adr/0001-storage-layout.md)
- [ADR-0002 — USB archive decommission](adr/0002-usb-archive-decommission.md)
- [ADR-0003 — Independent management plane and recovery source](adr/0003-independent-management-plane.md)
- [ADR-0004 — Fail-closed stateful Compose lifecycle](adr/0004-guarded-compose-lifecycle.md)
- [ADR-0005 — Optional shared APT cache](adr/0005-optional-package-cache.md)
- [ADR-0006 — Build-once, least-privilege OCI promotion](adr/0006-build-once-oci-promotion.md)
- [ADR-0007 — Digest-pinned Kubernetes image pulls](adr/0007-digest-pinned-kubernetes-image-pulls.md)
- [ADR-0008 — External Kubernetes deployer identity](adr/0008-external-kubernetes-deployer-identity.md)
- [ADR-0009 — Flux GitOps trust boundary](adr/0009-flux-gitops-trust-boundary.md)
- [ADR-0010 — Trusted local operations runner](adr/0010-trusted-local-operations.md)
- [ADR-0011 — Recovery root and environment configuration](adr/0011-recovery-root-and-configuration.md)
- [ADR-0012 — ARM portability, Forgejo and portal evaluation](adr/0012-portability-and-platform-product.md)
- [ADR-0013 — Risk-based DevSecOps and promotion](adr/0013-devsecops-policy-and-promotion.md)

## Sprint records

- [Sprint 00 — Brownfield discovery](sprints/00-bootstrap.md)
- [Sprint 01 — Management bootstrap](sprints/01-management-bootstrap.md)
- [Sprint 02 — Gitea](sprints/02-gitea.md)
- [Sprint 03 — Gotify](sprints/03-gotify.md)
- [Sprint 04 — Uptime Kuma](sprints/04-uptime-kuma.md)
- [Sprint 05 — APT-Cacher-NG](sprints/05-apt-cacher-ng.md)
- [Sprint 06 — Portable ARM64 CI](sprints/06-ci-foundation.md)
- [Sprint 07 — Native Gitea Actions CI](sprints/07-native-gitea-ci.md)
- [Sprint 08 — Application delivery foundation](sprints/08-application-delivery-foundation.md)
- [Sprint 09 — Dual OCI distribution](sprints/09-dual-oci-distribution.md)
- [Sprint 10 — Kubernetes delivery](sprints/10-kubernetes-delivery.md)
- [Sprint 11 — Deployment failure and rollback](sprints/11-deployment-failure-rollback.md)
- [Sprint 12 — Flux GitOps](sprints/12-flux-gitops.md)

## Operational evidence

- [APT cache benchmark](benchmarks/2026-10-04-apt-cacher-ng.md)
- [USB storage incident](incidents/2026-10-03-usb-storage.md)
- [Controlled Gitea outage](incidents/2026-10-04-gitea-controlled-outage.md)
- [Controlled Kubernetes deployment failure](incidents/2026-10-09-platform-hello-failed-rollout.md)
- [Kubernetes deployment rollback runbook](runbooks/kubernetes-deployment-rollback.md)
- [OPS-005 screenshots](evidence/ops-005/)
- [PLAT-006 screenshots](evidence/plat-006/)

## Current convergence point

As of 2026-10-09:

- five management-plane services have Ansible-owned guarded lifecycles;
- GitHub is canonical, protected `main` is enforced, and Gitea is a private one-way pull mirror;
- the R5C can prove source convergence across local `main`, GitHub and Gitea with a fetch-only Gitea remote;
- GitHub-hosted ARM64 CI and a physical R5C Gitea runner both validate the repository;
- repository validation includes Bash syntax, ShellCheck, Python parsing, Ruff, YAML parsing, yamllint, actionlint, Compose contract tests, Ansible syntax, and Compose rendering;
- `platform-hello` is built once, runtime-tested, Trivy-scanned, transferred across an isolated job boundary, integrity-checked, and published to GHCR;
- the publisher alone receives `packages: write`;
- the first verified GHCR artifact was published from commit `1ddd76c...` with registry digest `sha256:f3c542d3...`;
- the same qualified OCI artifact is independently retrievable from GHCR and Gitea by immutable digest;
- GHCR and Gitea report the same registry manifest digest for the promoted artifact;
- the Gitea package is associated with the mirrored source repository;
- repository-owned tooling handles OCI replication, parity checks, retrieval verification, package linking, and scoped Kubernetes deployment verification;
- the CI-qualified `platform-hello` artifact is running in Kubernetes by immutable digest;
- the R5C can reconcile the workload directly using namespace-scoped X.509 authentication without SSH or kubeadm administrator credentials;
- Kubernetes rollout, runtime digest identity, EndpointSlice resolution and in-cluster HTTP delivery are proven;
- a controlled failed rollout preserved application availability and was recovered through scoped Kubernetes rollback;
- Git desired state reconverged cleanly after recovery;
- Flux source-controller and kustomize-controller now run with a repository-owned hardening overlay;
- Flux reads canonical GitHub without repository credentials;
- application reconciliation impersonates a dedicated namespace-scoped ServiceAccount;
- initial Flux adoption caused no application rollout churn;
- live replica drift was automatically corrected back to unchanged Git state;
- intentional Git replica changes propagated to the cluster;
- suspended reconciliation allowed drift to persist, and resume restored Git state;
- Prometheus/Grafana, runtime alerting, backup/restore, OpenBao credential lifecycle and broader operational maturity remain pending.
