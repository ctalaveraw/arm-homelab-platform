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
- Ansible-owned enable/start lifecycle for all five services;
- SD-backed guarded state.

Remaining operational work such as HTTPS, backup/restore, and full fresh-host reconstruction is tracked under later maturity milestones rather than blocking M2.

## M3 — Application delivery

**Status: In progress.**

Completed:

- first application source under `apps/platform-hello`;
- ARM64/non-root local image acceptance;
- reusable HTTP readiness/content acceptance script;
- GitHub Actions `validate -> build-hello` dependency;
- Buildx Dockerfile pre-build check;
- successful hosted ARM64 build and runtime acceptance.

Next:

- build once and carry one explicit image identity through test/scan/publish;
- vulnerability scan;
- publish immutable image to GHCR;
- validate and populate local Gitea OCI distribution;
- deploy the CI-produced artifact into Kubernetes;
- verify endpoint and rollout.

Exit criteria:

- [x] application builds for ARM64;
- [x] CI performs application runtime acceptance;
- [x] Dockerfile quality check precedes build;
- [ ] security scan executes against the tested image;
- [ ] immutable image is published;
- [ ] verified artifact exists in external and local OCI distribution;
- [ ] Kubernetes pulls a CI-produced image;
- [ ] rollout and endpoint are verified.

## M4 — Operational evidence

**Status: Partially complete.**

Already demonstrated:

- controlled Gitea outage;
- monitoring detection;
- Gotify DOWN/UP notifications;
- guarded recovery.

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
