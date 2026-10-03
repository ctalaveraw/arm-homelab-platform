# ADR-0001: Management Plane Storage Layout

Status: Accepted
Date: 2026-10-01

## Context

The NanoPi R5C uses eMMC, removable SD storage,
and a USB HDD.

We require predictable paths for infrastructure
configuration, application state, and backups.

## Decision

/srv/platform:
Infrastructure repository and configuration.

/srv/services:
Logical namespace for persistent service data.

/srv/storage/state:
SD-backed additional persistent storage.

/srv/storage/archive:
HDD-backed archive and backup storage.

/srv/backups:
Logical backup namespace; physical placement TBD.

## Operational constraints

- Services must verify required mounts before startup.
- Storage references should use stable mount paths.
- Physical storage placement is service-dependent.
- Critical backups must also exist off-device.
- Secrets must not be committed to Git.

## Consequences

Applications can reference stable logical paths
without depending directly on block device names.

Ansible will eventually enforce this arrangement.

## Implementation Note — 2026-10-03

Persistent application data now follows:

/srv/storage/state/services/<service-name>

The service directory is created through Ansible and guarded
against accidental writes to an unmounted backing directory.

The USB archive is decommissioned as recorded in ADR-0002.
