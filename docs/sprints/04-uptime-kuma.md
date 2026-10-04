# OPS-005 — Uptime Kuma Deployment

Date: 2026-10-04
Status: Complete, subject to final browser persistence checks.

## Implementation

- Deployed Uptime Kuma 2.5.5 with SQLite.
- Configured uptime.lab.home.arpa through OpenWRT dnsmasq.
- Created SD-backed application storage using Ansible.
- Adapted the established Compose storage validation guard.
- Installed a guarded systemd-controlled Compose lifecycle.
- Configured Gitea and Gotify HTTP monitors.
- Integrated a dedicated Gotify notification application.

## Verification

- Initial Ansible execution created the persistent directory.
- Repeated execution converged with changed=0.
- Storage guard positive test passed.
- Incorrect storage-root override was rejected.
- Installed guard matched its source.
- Initial HTTP 302 redirected to the application.
- Following redirects returned HTTP 200.
- Notification integration test arrived in Gotify.
- Controlled Gitea DOWN and UP events generated real alerts.
- Stopping Kuma removed its running Compose container.
- Guarded startup successfully recreated the container.
- Both monitoring targets persisted after recreation.
- Application state uses /srv/storage/state/services/uptime-kuma.

## Observations

Persistent directory usage changed from approximately
1.5M to 368K across recreation. Disk usage equality
is not used as a persistence acceptance criterion.

## Limitations

- Initial access uses LAN HTTP; HTTPS remains pending.
- systemd oneshot does not continuously supervise HTTP health.
- Entire management-host failure is not independently monitored.
- Off-device SQLite backup/restore remains untested.
- Physical reboot verification remains pending.

## Incident evidence

See docs/incidents/2026-10-04-gitea-controlled-outage.md.
