# ADR-0002: Decommission the optional USB archive

Status: Accepted
Date: 2026-10-03

## Context

The optional USB HDD produced kernel read errors. The cause remains unresolved. The R5C uses eMMC for the OS/Docker and removable SD for application state.

## Decision

- Remove the USB archive from active fstab configuration.
- Retain `/srv/storage/archive` as an inactive namespace.
- Disable automatic SMART monitoring while the device is investigated.
- Keep the archive out of bootstrap and recovery dependencies.
- Validate the SD filesystem before starting stateful services.
- Store independent backup copies off-device.

## Consequences

Management services can operate without the unreliable archive. It is not a current backup destination.

Per-service guards check mounts and Compose bindings at startup. Positive mount checks and negative binding tests are recorded in the service evidence. Physical SD removal during active writes has not been tested.

Forgejo keeps this storage contract and separate state from Gitea. Its [migration record](../runbooks/gitea-to-forgejo.md) records the verified off-device archive; scheduled encrypted backups and restore remain open work.

## Follow-up

Investigate the USB device, cable and power separately. Test backup restoration without reintroducing the archive as a required dependency.
