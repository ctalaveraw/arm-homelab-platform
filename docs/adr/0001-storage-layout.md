# ADR-0001: Management plane storage layout

Status: Accepted; the USB archive role was retired by ADR-0002.
Date: 2026-10-01

## Context

The R5C boots from eMMC and stores application data on removable SD. Its original USB archive proved unreliable. Services need stable paths and explicit checks before writing state.

## Decision

| Path | Use |
| --- | --- |
| `/srv/platform` | Infrastructure checkout and deployment configuration |
| `/srv/storage/state/services/<service>` | Active SD-backed application state |
| `/srv/backups` | Local checkpoints; copy recovery material off-device |
| `/srv/services` | Earlier logical namespace; current service data uses the SD path above |
| `/srv/storage/archive` | Inactive namespace after USB decommission |

Ansible creates service directories. Systemd storage guards verify the actual `storage_sdcard` ext4 mount and rendered bind sources before activation. Docker's data root remains on eMMC.

Forgejo and its runner have separate state from retained Gitea data. Runner registration is `services/forgejo-runner/runner.yml`, UID/GID 10001, mode 0600. See the [path reference](../runbooks/forgejo-reference-map.md#repository-and-host-paths).

## Consequences

Stable mount paths keep application configuration independent of block-device names. A missing or redirected mount must fail startup.

The USB archive is not a backup destination. Consistent off-device copies and restore tests remain separate responsibilities. Secrets stay outside public Git.

## Evidence

- [Initial host snapshot](../architecture/r5c-baseline.md)
- [USB archive decision](0002-usb-archive-decommission.md)
- [Guarded lifecycle](0004-guarded-compose-lifecycle.md)
- [Forgejo migration](../runbooks/gitea-to-forgejo.md)
