# Engineering Evidence Ledger

Purpose: Record verifiable engineering work and
preserve the reasoning behind implementation.

## EVIDENCE-001: Management Storage Baseline

Date: 2026-10-01

Problem:
The management host initially lacked documented
storage and service namespace conventions.

Implementation:
- Established /srv/platform.
- Established /srv/services.
- Established /srv/storage/state.
- Established /srv/storage/archive.
- Recorded ADR-0001.

Verification:
- findmnt --verify passed.
- Active mounts inspected.
- Filesystem capacity verified.

Evidence:
- Commit 3e8e218.
- docs/adr/0001-storage-layout.md.
- docs/architecture/r5c-baseline.md.

## EVIDENCE-002: SD Storage Migration

Date: 2026-10-02

Change:
Replaced the original 32 GB SD card with a
128 GB SD card.

Preserved:
- Filesystem label: storage_sdcard
- Mount point: /srv/storage/state
- Filesystem type: ext4

Observed:
- New device size: 119.2 GiB.
- Filesystem size: approximately 117 GiB.
- Available capacity: approximately 109 GiB.
- Active filesystem mounted rw,noatime.
- fstab uses LABEL=storage_sdcard.
- findmnt --verify passed.

Outstanding at time of measurement:
- [ ] Validate persistence after reboot.
- [ ] Enforce service mount dependencies.

Update (2026-10-04): per-service SD storage guards were
implemented and tested. Full-host reboot verification
remains a separate outstanding test.

Learning objective:
Explain LABEL versus UUID versus mount point,
and the operational effects of nofail/automount.


## EVIDENCE-003: Ansible Management Baseline

Date: 2026-10-03

Implementation:
- Created local R5C inventory.
- Added architecture and SD storage assertions.
- Established reusable common role.
- Declaratively managed package and directory state.

Verification:
- Preflight passed.
- Required SD filesystem validated.
- Directory execution initially changed one resource.
- Subsequent execution reported changed=0.

Evidence:
- Commit 03d217c.
- Commit 48465e0.

Limitations:
- Full fresh-host reconstruction remains untested.

## EVIDENCE-004: Docker Runtime Bootstrap

Date: 2026-10-03

Implementation:
- Created docker_host role.
- Installed docker.io, docker-cli and docker-compose.
- Declaratively enabled and started docker.service.
- Retained Docker data root on eMMC.

Verification:
- First corrected package execution changed=1.
- Subsequent execution changed=0.
- Docker client/server verified: 26.1.5.
- Standalone Compose verified: 2.26.1.
- Docker and containerd active.
- Docker enabled at boot.
- Data root: /var/lib/docker.

Engineering lesson:
Idempotent configuration does not guarantee that
the declared dependency list is complete. Runtime
verification exposed the initially missing Docker CLI.

Evidence:
- Commit 989c5d8.

## EVIDENCE-005: Gotify Notification Service

Date: 2026-10-04

Problem:
The management platform lacked an operational
notification destination for future CI/CD and incidents.

Implementation:
- Deployed Gotify 3.1.1 on ARM64.
- Reused Ansible, Compose and guarded systemd lifecycle.
- Persisted application state on validated SD storage.
- Integrated a DNS-based service identity.

Verification:
- Positive and negative storage tests passed.
- First authenticated API notification returned HTTP 200.
- Browser receipt independently confirmed.
- Application and message survived container recreation.
- Service active and enabled after recreation.

Trade-offs:
- LAN HTTP is temporary.
- Gotify is now monitored through Uptime Kuma, although both
  services share the same management-host failure domain.
- Off-device application restore remains untested.

## EVIDENCE-006: Service Monitoring and Recovery

Date: 2026-10-04

Implementation:
- Deployed persistent Uptime Kuma on ARM64.
- Established Gitea and Gotify HTTP monitoring.
- Integrated Gotify incident notifications.

Verification:
- Positive and negative storage tests passed.
- Ansible converged with changed=0.
- Controlled Gitea outage generated a real DOWN alert.
- Guarded recovery generated a subsequent UP alert.
- Monitoring targets survived Kuma container recreation.

Trade-offs:
- Monitoring shares a failure domain with notification delivery.
- Off-device recovery and full-host outage detection are pending.

Evidence:
- docs/sprints/04-uptime-kuma.md
- docs/incidents/2026-10-04-gitea-controlled-outage.md

## EVIDENCE-007: Shared APT Package Cache

Date: 2026-10-04

Implementation:
- Deployed ARM64 APT-Cacher-NG.
- Reused Ansible, Compose and guarded systemd lifecycle.
- Persisted cache data on SD-backed ext4.
- Declaratively enabled and started the service.
- Added HTTP monitoring through Uptime Kuma.

Verification:
- Ansible converged with changed=0.
- Storage guard rejected an incorrect binding.
- First package request: 199.713 ms.
- Identical subsequent request: 15.229 ms.
- SHA-256 checksums matched.
- Server logs demonstrated package-cache reuse.
- Cache survived container recreation.
- Post-restart retrieval completed in 15.813 ms.

Limitations:
- Single-package comparison; not a full CI benchmark.
- Network source ACL verification remains pending.
- A hard capacity quota has not been established.
- Full-host reboot and expiry execution remain untested.

Evidence:
- docs/benchmarks/2026-10-04-apt-cacher-ng.md
- docs/sprints/05-apt-cacher-ng.md

## EVIDENCE-008: Portable ARM64 Repository CI

Date: 2026-10-04

Implementation:
- Kept GitHub Actions YAML thin: checkout, dependency bootstrap and one
  repository-owned validation entrypoint.
- Added scripts/ci/bootstrap.sh and scripts/ci/validate.sh.
- Added three Python unittest checks enforcing Compose storage, restart
  policy, and explicit binding contracts.
- Validation runs on GitHub's ARM64 hosted runner and locally.

Verification:
- Three successive GitHub Actions runs completed successfully.
- Run #3 reported aarch64, passed the three contract tests and completed
  full repository validation.
- The hosted run also performed ShellCheck.

Evidence:
- Commit a5d3222: portable validation entrypoints.
- Commit 3e58f61: Compose safety-contract tests.
- https://github.com/ctalaveraw/arm-homelab-platform/actions/runs/37186219090
- docs/sprints/06-ci-foundation.md

Limits:
- Static validation, not application integration or deployment testing.
- It does not reproduce the physical SD mount on a hosted runner.

## EVIDENCE-009: Canonical GitHub and Private Gitea Pull Mirror

Date: 2026-10-04

Implementation:
- Retained GitHub as off-device canonical and recovery repository.
- Created the Gitea repository using its native pull-mirror import.

Verification:
- Gitea showed the repository as a GitHub mirror with recent sync.
- Gitea's displayed main HEAD and GitHub ls-remote both matched
  3e58f61e8855b41623490c560f90f774b72ca3f0.

Limits:
- The original observation did not establish a recurring synchronization SLA.
- GitHub Actions history/secrets are not replicated by a Git mirror.

Update (2026-10-04):
- A repository-scoped Gitea Actions runner is now operational on the R5C.
- Forced mirror synchronization generated a push event that triggered native validation.
- GitHub remains canonical; the mirror remains one-way.

## EVIDENCE-010: Native Gitea Actions on Physical ARM64

Date: 2026-10-04

Implementation:
- Built a purpose-specific ARM64 Gitea runner image.
- Registered runner at repository scope.
- Persisted runner identity on guarded SD storage.
- Ran the runner as UID/GID 10001 without privileged mode or a host Docker socket.
- Reused the same repository-owned bootstrap and validation entrypoints as GitHub Actions.
- Added Ansible ownership for runner storage, systemd unit installation, enablement and startup.

Verification:
- Runner storage playbook converged with changed=0.
- Runner declared successfully to Gitea.
- Gitea Actions run #1 completed successfully on the physical NanoPi R5C.
- Run details showed a push trigger on main after mirror synchronization.
- Four Compose safety-contract tests passed.

Trade-offs:
- Host-mode jobs share the trusted runner container environment.
- The runner is for trusted repository validation, not arbitrary untrusted PR execution.
- No deployment, registry or Kubernetes credentials are present.

Evidence:
- docs/sprints/07-native-gitea-ci.md
- docs/evidence/plat-006/

What I learned:
A self-hosted runner is an execution boundary, not merely another service. Registration scope, persisted identity, runtime privilege, and access to the host Docker daemon materially change the risk profile.

## EVIDENCE-011: First ARM64 Application Build and Runtime Acceptance

Date: 2026-10-04

Problem:
Repository validation existed, but the platform had not yet proven that CI could build and exercise an application image.

Implementation:
- Added apps/platform-hello with a minimal static HTML workload.
- Built the image for Linux ARM64.
- Ran the application as UID/GID 10001.
- Added scripts/ci/test-hello.sh for architecture, runtime identity, readiness and content checks.
- Added a dependent GitHub Actions build-hello job using needs: validate.
- Added Docker Buildx --check before the build job.
- Upgraded GitHub checkout actions to v5, removing the observed Node.js 20 warning.

Verification:
- Local ARM64 image and HTTP acceptance passed.
- Readiness polling demonstrated that container-running state can precede HTTP readiness.
- GitHub-hosted ARM64 validate and build-hello jobs both passed.
- The application build remains gated on repository validation.

Trade-offs:
- The test script currently builds the image internally.
- The image is ephemeral on the hosted runner and is not yet published.
- Scan, registry publication, immutable digest capture and Kubernetes delivery remain pending.

What I learned:
CI success must be tied to the artifact produced by the current source. A stale local image or an independent rebuild after testing can break artifact identity and create misleading evidence.

## Evidence Template

### EVIDENCE-XXX: Title

Date:
Problem:
Implementation:
Verification:
Trade-offs:
Evidence:
What I learned:
