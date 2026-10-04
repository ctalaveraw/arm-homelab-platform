# Sprint 2 — Gotify Deployment

Date: 2026-10-04
Status: PLAT-005 complete.

## Implementation

- Deployed Gotify 3.1.1 via Docker Compose.
- OpenWRT dnsmasq provides gotify.lab.home.arpa.
- Ansible manages /srv/storage/state/services/gotify.
- systemd owns the Compose lifecycle.
- Startup guard validates actual SD mount and Compose binding.
- Host binding is explicitly configured through local .env.
- Populated .env and application tokens are excluded from Git.

## Verification

- Ansible converged with changed=0.
- Installed guard matched its source.
- Positive storage test passed.
- Incorrect storage-root override was rejected.
- HTTP readiness returned 200.
- ARM Homelab Platform application was created.
- First notification delivered through authenticated API.
- API returned HTTP 200 and message ID 1.
- systemd stop removed the Compose container.
- Guarded restart recreated the container.
- Application and notification survived recreation.
- Persistent data measured 84K before and after.
- gotify.service confirmed active and enabled.

## Limitations

- Initial deployment uses LAN HTTP.
- Application data has not undergone off-device restore testing.
- systemd oneshot does not continuously supervise HTTP health.
- Initial administrator credential remains a local bootstrap
  secret until independently cleaned up.
- SD mount guard protects startup, not physical removal
  during active application writes.

## Next

Evaluate lightweight monitoring, establish shared HTTPS,
then continue to PLAT-006: Gitea Actions runner.
