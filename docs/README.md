# Documentation Index

This directory separates **current-state documentation** from **historical evidence**. Historical sprint, incident, and benchmark records are intentionally not rewritten to pretend later capabilities existed at the time.

## Current state

- [Architecture overview](architecture/overview.md) — current implemented and planned component relationships.
- [Roadmap](roadmap.md) — milestone-level progress toward application delivery.
- [Backlog](backlog.md) — active and queued work items.
- [CI, mirroring and OCI publication](ci.md) — GitHub/Gitea CI behavior, validation contracts, artifact handoff, and GHCR publication.
- [Engineering evidence ledger](interview/engineering-evidence.md) — interview-oriented proof of implementation and verification.
- [R5C baseline](architecture/r5c-baseline.md) — original brownfield snapshot plus a current-state delta.

## Architecture decisions

- [ADR-0001 — Management plane storage layout](adr/0001-storage-layout.md)
- [ADR-0002 — USB archive decommission](adr/0002-usb-archive-decommission.md)
- [ADR-0003 — Independent management plane and recovery source](adr/0003-independent-management-plane.md)
- [ADR-0004 — Fail-closed stateful Compose lifecycle](adr/0004-guarded-compose-lifecycle.md)
- [ADR-0005 — Optional shared APT cache](adr/0005-optional-package-cache.md)
- [ADR-0006 — Build-once, least-privilege OCI promotion](adr/0006-build-once-oci-promotion.md)

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

## Operational evidence

- [APT cache benchmark](benchmarks/2026-10-04-apt-cacher-ng.md)
- [USB storage incident](incidents/2026-10-03-usb-storage.md)
- [Controlled Gitea outage](incidents/2026-10-04-gitea-controlled-outage.md)
- [OPS-005 screenshots](evidence/ops-005/)
- [PLAT-006 screenshots](evidence/plat-006/)

## Current convergence point

As of 2026-10-05:

- five management-plane services have Ansible-owned guarded lifecycles;
- GitHub is canonical, protected `main` is enforced, and Gitea is a private one-way pull mirror;
- the R5C can prove source convergence across local `main`, GitHub and Gitea with a fetch-only Gitea remote;
- GitHub-hosted ARM64 CI and a physical R5C Gitea runner both validate the repository;
- repository validation includes Bash syntax, ShellCheck, Python parsing, Ruff, YAML parsing, yamllint, actionlint, Compose contract tests, Ansible syntax, and Compose rendering;
- `platform-hello` is built once, runtime-tested, Trivy-scanned, transferred across an isolated job boundary, integrity-checked, and published to GHCR;
- the publisher alone receives `packages: write`;
- the first verified GHCR artifact was published from commit `1ddd76c...` with registry digest `sha256:f3c542d3...`;
- Gitea OCI replication, independent digest retrieval, backup/restore, and Kubernetes delivery remain pending.
