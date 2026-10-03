# Sprint 0 — Brownfield Discovery

Status: In Progress

## Completed

### Session 0.1 — Repository Foundation
- Initialized /srv/platform.
- Established storage semantics.
- Created ADR-0001.
- Commit: 490ad49.

### Session 0.2 — System Baseline
- Validated filesystem mounts.
- Captured hardware and OS inventory.
- Created r5c-baseline.md.
- Commit: bd5d5c5.

### Post-baseline Changes
- Installed Ansible from Debian repositories.
- ansible [core 2.19.11]

## Remaining

- [ ] Establish private external Git remote.
- [ ] Verify off-device push.
- [ ] Review existing bootstrap_shell.sh.
- [ ] Close Sprint 0.

## Sprint Acceptance Criteria

A fresh system can retrieve the platform repository
without depending on the NanoPi's future Gitea instance.
