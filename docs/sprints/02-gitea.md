# Sprint 2 — Gitea Deployment

Date: 2026-10-03
Status: PLAT-004 complete.

## Implementation

- Deployed Gitea 1.27.3 using Docker Compose.
- Used SQLite for the initial single-node deployment.
- Established application state under
  /srv/storage/state/services/gitea.
- Managed persistent directories with Ansible.
- Established gitea.lab.home.arpa through OpenWRT dnsmasq.
- Separated canonical service identity from host binding IP.
- Implemented a Python SD storage and Compose binding guard.
- Installed a systemd-controlled Compose lifecycle.
- Enabled guarded startup at boot.

## Verification

- Ansible converged with changed=0.
- Positive SD storage verification passed.
- Unsafe Compose storage override was rejected.
- Installed guard matched the reviewed Python source.
- First Gitea deployment completed successfully.
- Gitea HTTP endpoint returned 200.
- systemd stop removed the Compose container.
- systemd start recreated the container.
- Existing installation, administrator and
  admin/platform-smoke-test repository persisted.
- SQLite database initialized successfully after recreation.
- gitea.service verified active and enabled.

## Findings

- Detached Compose startup does not imply HTTP readiness.
- An immediate curl after container recreation returned HTTP 000.
- Readiness retry subsequently returned HTTP 200.
- Ansible idempotency alone did not detect an earlier incorrect
  copy source; artifact comparison exposed the mistake.

## Limitations and Follow-up

- Initial access currently uses LAN HTTP.
- Implement HTTPS before broader or sensitive use.
- Restrict account registration to intended users.
- systemd oneshot does not continuously supervise container health.
- Off-device application backup/restore remains untested.
- Preserve app.ini, SQLite state, SSH keys and secrets outside Git.

## Next

PLAT-005: Gotify notifications.
