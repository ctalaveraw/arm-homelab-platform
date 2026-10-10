# Platform Engineering Roadmap

## Current objective

Mature the proven ARM64 delivery/GitOps foundation into a portable, recoverable DevSecOps platform: observability and alerting first, then fresh-node bootstrap, controlled secrets, verified restore, policy-enforced supply-chain promotion and approved operations. See the [platform charter](vision/platform-charter.md), [design gates](planning/design-gates.md) and [93-objective register](planning/objectives.md).

## M0 — Bootstrap and discovery

**Status: Complete.**

Exit criteria met:

- repository initialized;
- brownfield baseline captured;
- storage decisions documented;
- external GitHub recovery remote verified.

## M1 — Management host as code

**Status: Implemented on the existing R5C; fresh-host rebuild still untested.**

Exit criteria met:

- Ansible inventory and preflight;
- common host role;
- Docker/Compose installation;
- repeated/idempotent execution;
- guarded persistent service directories.

## M2 — Development infrastructure

**Status: Complete for the current lab scope.**

Implemented:

- Gitea, Gotify, Uptime Kuma, and APT-Cacher-NG;
- repository-scoped Gitea Actions runner;
- GitHub canonical source plus private one-way Gitea mirror;
- GitHub-hosted ARM64 validation;
- physical R5C ARM64 Gitea validation;
- protected GitHub `main`;
- source parity check across GitHub, Gitea and controller-local `main`;
- Ansible-owned enable/start lifecycle for all five services;
- SD-backed guarded state.

Remaining operational work such as HTTPS, backup/restore, and full fresh-host reconstruction is tracked under later maturity milestones rather than blocking M2.

## M3 — Application delivery

**Status: Complete.**

Completed:

- first application source under `apps/platform-hello`;
- ARM64/non-root local image acceptance;
- Buildx Dockerfile pre-build check;
- build-once GitHub-hosted ARM64 image production;
- runtime readiness/content acceptance against the exact built image;
- Trivy vulnerability and secret scanning of the tested image;
- repository quality gates with ShellCheck, Ruff, yamllint and actionlint;
- isolated cross-job image transfer;
- archive checksum verification;
- Docker image-ID verification before and after transfer;
- least-privileged GHCR publisher with `packages: write`;
- successful GHCR publication and immutable registry digest capture;
- independent full retrieval from GHCR by digest;
- identity-preserving replication of the qualified artifact into Gitea OCI;
- matching GHCR/Gitea registry manifest digests;
- independent full retrieval from Gitea by digest;
- Gitea package association with the mirrored source repository;
- repository-owned OCI replication, parity, retrieval and package-link tooling.

First verified publication:

```text
commit: 1ddd76c14a35f974d06dbd1ed7e3c4c14475c92d
digest: sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e
```

Kubernetes delivery completed:

- raw repository-owned Namespace, Deployment and ClusterIP Service manifests;
- immutable GHCR digest deployment;
- first-pull proof from a worker without the application cached;
- successful rollout and Ready Pod;
- runtime image digest matched the CI-qualified registry digest;
- EndpointSlice and in-cluster Service-DNS HTTP acceptance;
- namespace-scoped deployment RBAC;
- direct R5C-to-Kubernetes authentication with a scoped X.509 identity;
- repository-owned deployment and runtime-verification tooling.

Exit criteria:

- [x] application builds for ARM64;
- [x] CI performs application runtime acceptance;
- [x] Dockerfile quality check precedes build;
- [x] security scan executes against the tested image;
- [x] immutable image is published externally;
- [x] verified artifact exists in external and local OCI distribution;
- [x] Kubernetes pulls a CI-produced image by digest;
- [x] rollout and endpoint are verified.

## M4 — Operational evidence

**Status: Complete for the current delivery milestone.**

Demonstrated:

- controlled Gitea outage;
- monitoring detection;
- Gotify DOWN/UP notifications;
- guarded recovery;
- CI failure/recovery during artifact publication development;
- integrity verification across isolated CI jobs;
- controlled Kubernetes deployment failure;
- registry `NotFound`, `ErrImagePull`, and `ImagePullBackOff` diagnosis;
- failed rollout detection through native Kubernetes state and Events;
- preservation of the previous Ready replica during failed RollingUpdate;
- EndpointSlice readiness-state inspection;
- HTTP availability during the failed rollout;
- scoped rollback to the known-good Pod template;
- post-rollback HTTP verification;
- reconciliation back to unchanged Git desired state;
- committed incident record and recovery runbook.

Automated runtime alerting remains a later observability milestone under
PLAT-013 rather than a blocker for M4.

## M5 — GitOps

**Status: Complete.**

Implemented:

- Ansible-managed Flux 2.9.6 client on the independent R5C;
- repository-owned Flux controller installation generated from upstream;
- source-controller and kustomize-controller only;
- repository-owned hardening overlay;
- namespace-local Flux object watches;
- cross-namespace Flux references disabled;
- remote Kustomize bases disabled;
- fail-closed default reconciliation ServiceAccount;
- public GitHub canonical source consumed without Git credentials;
- dedicated namespace-scoped application reconciliation ServiceAccount;
- application inventory limited to Deployment and Service;
- immutable digest delivery preserved under Flux;
- live drift correction;
- intentional Git desired-state propagation;
- suspend and resume behavior;
- retained scoped X.509 break-glass path.

Verification proved that runtime drift is corrected when reconciliation is
active, persists while the application Kustomization is suspended, and is
corrected again immediately after reconciliation resumes.

Normal application reconciliation is now pull-based from protected Git rather
than operator-driven application of manifests.

## M6 — Observable, reproducible and recoverable operations (active roadmap)

**Status: Queued, not complete.** Deliver the following sequentially, allowing small prerequisite quality/security checks to join the relevant sprint without creating competing active milestones:

1. **PLAT-012 — Prometheus/Grafana:** metrics for node, K8s, Flux and R5C where practical; retention, availability and resource budget, failing-scrape evidence. Seed only necessary configuration, with a later service-integration objective (OBS-001, OPS-017/018).
2. **PLAT-013 — Gotify runtime alerting:** meaningful alert thresholds, routing, deduplication, recovery and missing-signal tests (OBS-002, OPS-012).
3. **PLAT-014/015 — fourth Pi and reproducible join:** pin/lint Ansible, optional approved APT cache, day-zero versus host-convergence distinction, role/network/SD failure tests (CI-002, OPS-010/011, DR-001..003).
4. **PLAT-016 — OpenBao and identity:** define independent encryption/PKI recovery first; short-lived routine credentials and renewal/revocation. **OPS-007 shared trusted HTTPS is a prerequisite for production-like management API/secret integrations**, not an excuse to delay monitoring (OPS-013/014, DR-004/005/011).
5. **PLAT-017/018 — encrypted off-device backups and isolated disaster recovery:** consistent Gitea/OCI/config recovery, standalone reconstruction without live forge/vault/R5C, time-bound exercise and truthfully measured targets (DR-004..012).

**Design targets:** recovery time objective **4 hours** and recovery point objective **1 hour** for a classified *critical* scope, **not achieved guarantees**. Define data/services covered, incident timing, spare hardware availability, restore-key redundancy, consistency, backup frequency and multiple isolated drills before claiming either goal.

Ansible's current management preflight assumes a booted ARM64 host and mounted labeled SD. It is not day-zero recovery; DR-001..003 must establish the missing preconditions.

## M7 — Secure delivery and continuous assurance (planned)

Extend the working build-once artifact contract, not replace it. Threat model and SCM/runner governance; appropriate SAST/SCA/IaC policy; image SBOM, builder/source provenance, digest signing, verifier and approved promotion PR; Kubernetes admission/workload/network/runtime policy; vulnerability rescan/remediation, exceptions and incident response. Use measured Observe → Warn → Block → Verify progression, with owner and expiry on exceptions. Keep CI, operations and Flux distinct authorities.

Key tickets: SEC-001 and SEC-002..031; REL-001..006; CI-003..011. Tools are selected for coverage and ARM practicality; passing multiple overlapping scanners is not the definition of success.

## M8 — Independent trusted local operations (planned)

Build a *separate* approval-gated Gitea operations runner after trust, baseline recovery and service visibility prerequisites. Workflows authorize approved operations, Ansible converges R5C hosts, tested Bash/Python helpers perform pre/post checks, and Flux remains the sole routine reconciler of selected Kubernetes application resources. No privileged credentials for the existing validation runner; no dependence on live Gitea to restore Gitea.

Key tickets: OPS-008/009/015, ENG-001..005, CI-006/009. Existing manual recovery remains operational throughout.

## M9 — Portability, development experience and portfolio capstone (future/evaluate)

- Demonstrate a secondary target with explicit ARM-first platform contracts; optionally Terraform-provisioned Proxmox VMs, Ansible convergence and independent Flux reconciliation (PORT-001/002/004/005).
- Rehearse Forgejo migration **in isolation** with proven compatibility/export/rollback; no immediate switch or assumed drop-in image migration (PORT-003).
- Evaluate Backstage only with multiple services/personas and a justified self-service golden-path experiment (IDP-001/002).
- Maintain off-lab contributions using portable, simulated and physical validation tiers (DX-001..003).
- Human-edit and reorganize documentation for cold readers/evaluators; credible evidence and explicit current-vs-target labels (DOC-001/002).

## Scope discipline and acceptance

The [backlog](backlog.md) enumerates 93 additional objectives with [exit evidence and prerequisites](planning/objectives.md). This is a catalog of **planned/evaluation work**, not 93 simultaneous active projects. One active milestone remains the policy. Gate-specific design details may change through reviewed ADRs. Off-lab GitHub checks establish portable P or simulated S evidence; physical H testing must not be assumed passed.

## Sprint cadence

Each focused session follows:

1. Orient.
2. Explain the mechanism.
3. Implement.
4. Verify.
5. Troubleshoot or inject a failure when useful.
6. Document evidence.
7. Commit/PR.
8. Complete a short knowledge gate before advancing delivery.
