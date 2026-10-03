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

## Evidence Template

### EVIDENCE-XXX: Title

Date:
Problem:
Implementation:
Verification:
Trade-offs:
Evidence:
What I learned:
