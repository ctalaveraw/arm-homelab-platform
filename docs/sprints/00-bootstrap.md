# Sprint 0 — Brownfield Discovery

Status: Complete — external recovery established.

## Completed

### Session 0.1 — Repository Foundation
- Initialized /srv/platform.
- Established storage semantics.
- Created ADR-0001.
- Commit: 3e8e218.

### Session 0.2 — System Baseline
- Validated filesystem mounts.
- Captured hardware and OS inventory.
- Created r5c-baseline.md.
- Commit: 9946c4d.

### Post-baseline Changes
- Installed Ansible from Debian repositories.
- ansible [core 2.19.11]

## Closure

- [x] Establish external GitHub remote.
- [x] Verify off-device push.
- [x] Close bootstrap/discovery scope.
- [ ] Review bootstrap_shell.sh (deferred to OPS-003).

## Sprint Acceptance Criteria

A fresh system can retrieve the platform repository
without depending on the NanoPi's future Gitea instance.

## Post-Baseline Storage Change (2026-10-02)

- Replaced original SD card with a 128 GB card.
- Retained LABEL=storage_sdcard.
- Retained /srv/storage/state mount point.
- Verified active mount and usable capacity.
- findmnt --verify passed.
- SD automount activation observed after subsequent reboot.

The original baseline is retained as a historical
snapshot rather than rewritten after the change.
