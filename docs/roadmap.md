# Platform Engineering Roadmap

## Current objective

Deliver a reproducible ARM64 application artifact from canonical Git source into the existing Raspberry Pi Kubernetes cluster while preserving an independently recoverable management plane.

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

**Status: Partially complete.**

Already demonstrated:

- controlled Gitea outage;
- monitoring detection;
- Gotify DOWN/UP notifications;
- guarded recovery;
- CI failure/recovery during artifact publication development;
- integrity verification across isolated CI jobs.

Still required:

- controlled application/deployment failure;
- detection;
- rollback/recovery;
- committed incident record and runbook.

## M5 — GitOps

Introduce Flux only after the push-based image build/publication/deployment path is understood and verified.

Target:

- desired state in Git;
- Flux reconciles the cluster;
- CI stops directly owning runtime deployment.

## M6 — Operational maturity

- shared trusted HTTPS;
- off-device Restic backup/restore;
- Gitea/package recovery;
- observability;
- node reconstruction;
- secrets management;
- management-plane disaster recovery.

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
