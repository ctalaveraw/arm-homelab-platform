# ADR-0004: Guarded stateful Compose lifecycle

Status: Accepted
Recorded: 2026-10-04

## Context

If the SD mount is missing, its path can expose an underlying eMMC directory. Docker must not create a new state directory there and start an apparently empty application.

## Decision

Ansible installs each service's directories, storage guard and systemd unit. Before activation:

- Require and inspect the mounted filesystem.
- Verify ext4 and label `storage_sdcard`.
- Reject symlink/path redirection.
- Check the rendered Compose bind sources.
- Require `create_host_path: false`.
- Keep the Compose restart policy at `no`.
- Start through the systemd unit.

Service-specific guards remain separate until shared behavior warrants a common implementation.

## Implementation

Current forge units are `forgejo.service` and `forgejo-runner.service`, installed from their matching Compose directories. The runner also requires `/srv/storage/state/services/forgejo-runner/runner.yml` with UID/GID 10001 and mode 0600.

Ansible deployment and service activation passed during the migration. Positive/negative guard behavior is covered by the repository tests. See the [current paths](../runbooks/forgejo-reference-map.md#repository-and-host-paths) and [migration record](../runbooks/gitea-to-forgejo.md).

## Consequences

Invalid storage or bindings stop activation. The contract covers startup checks; unexpected SD loss during writes still requires application recovery.

An active systemd oneshot does not continuously check container health. Availability monitoring, alert delivery, off-device backup and full-host recovery need their own checks. Full reboot recovery remains unverified.
