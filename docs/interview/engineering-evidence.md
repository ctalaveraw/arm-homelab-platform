# Engineering Evidence Ledger

Purpose: Record verifiable engineering work and
preserve the reasoning behind implementation.

Do not claim planned work as completed work.

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

Outstanding:
- [ ] Validate persistence after reboot.
- [ ] Enforce service mount dependencies.

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

## Evidence Template

### EVIDENCE-XXX: Title

Date:
Problem:
Implementation:
Verification:
Trade-offs:
Evidence:
What I learned:
