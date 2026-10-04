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

## Evidence Template

### EVIDENCE-XXX: Title

Date:
Problem:
Implementation:
Verification:
Trade-offs:
Evidence:
What I learned:
