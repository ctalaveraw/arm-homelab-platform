# ADR-0004: Fail-Closed Stateful Compose Lifecycle

Status: Accepted
Recorded: 2026-10-04 (retrospective)

## Context

The R5C boots from eMMC and stores application state
on removable ext4 SD storage.

A missing mount can expose an underlying eMMC directory.
Docker bind mounts must not silently redirect state there.

## Decision

Use Ansible to provision persistent application directories,
storage guards and systemd units.

For each SD-backed stateful service:

- Require the expected mount through systemd.
- Activate and inspect the actual filesystem.
- Verify filesystem type and label.
- Reject unsafe symlink or storage-path redirection.
- Validate the fully interpolated Compose bind source.
- Use create_host_path: false for stateful bind mounts.
- Set the Compose application restart policy to "no".
- Start the workload through its guarded systemd unit.

Application-specific guards are temporarily duplicated
rather than prematurely generalized.

## Consequences

Service startup fails closed when required storage
or the declared Compose binding is invalid.

Ansible provides repeatable provisioning, artifact
installation, configuration validation, boot enablement
and initial service activation for the original five
management-plane services recorded below.

This design protects startup, not unexpected physical
SD removal during active writes.

A systemd oneshot reporting active (exited) also does
not prove continued application availability.

HTTP monitoring, off-device backup/restore and complete
host reconstruction remain distinct responsibilities.


## Implementation update — 2026-10-04

At this checkpoint, the guarded lifecycle covered:

- Gitea
- Gitea Actions runner
- Gotify
- Uptime Kuma
- APT-Cacher-NG

The runner adds a separate contract: its persisted `.runner` identity must exist on the expected SD-backed path with UID/GID 10001 and mode 0600 before startup.

## Forgejo amendment — 2026-11-17

Current lifecycle units are `forgejo.service` and `forgejo-runner.service`, installed from `compose/forgejo/` and `compose/forgejo-runner/`. Guards and Ansible playbooks use the corresponding Forgejo names. The fresh runner identity is `/srv/storage/state/services/forgejo-runner/runner.yml`, not the dated `.runner` format above; it requires UID/GID 10001 and mode 0600. See [all current paths](../runbooks/forgejo-reference-map.md#repository-and-host-paths). This configuration change does not transfer the earlier host acceptance to the new services.
