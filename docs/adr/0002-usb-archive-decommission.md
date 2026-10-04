# ADR-0002: Decommission Optional USB Archive

Status: Accepted
Date: 2026-10-03

## Context

The R5C uses eMMC for the operating system and a
removable SD filesystem for additional application state.

The optional USB HDD produced kernel-level read errors.
Its hardware reliability has not been established.

## Decision

- Remove the USB archive from active fstab configuration.
- Do not require the archive during management bootstrap.
- Retain /srv/storage/archive as an inactive namespace.
- Disable automatic SMART monitoring pending investigation.
- Keep Docker's data root on eMMC for this iteration.
- Require successful SD validation in management preflight.

## Consequences

The management plane can continue developing without
depending on the USB HDD.

The archive is not currently a backup destination.

A successful Ansible preflight alone does not guarantee
that future containers have safe mount dependencies.
Those guards must be implemented during service deployment.

## Follow-up

- Investigate USB HDD, connection and power out of band.
- Establish functional off-device application backups.
- Test storage failure behavior before Gitea deployment.

## Implementation Update — 2026-10-04

The Gitea, Gotify, Uptime Kuma and APT-Cacher-NG deployments now use application-specific startup guards.

Positive mount-validation tests and negative Compose-binding tests passed. Container recreation and persisted application/cache state were independently verified.

Physical SD removal during active application writes has not been tested. This remains outside the completed startup-safety acceptance criteria.

The USB archive remains decommissioned and is not a backup destination.
