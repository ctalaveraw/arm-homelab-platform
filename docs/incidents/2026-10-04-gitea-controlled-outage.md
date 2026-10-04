# INC-001 — Controlled Gitea Outage

Date: 2026-10-04
Classification: Planned fault-injection exercise
Outcome: Recovered successfully

## Objective

Validate service failure detection, notification delivery,
guarded recovery and post-recovery monitoring.

## Timeline (America/New_York)

- 01:11:18 — Operator intentionally stopped gitea.service.
- Gitea became inactive; direct HTTP request returned 000.
- Uptime Kuma observed connection refusal and progressed
  through Pending to DOWN.
- Gotify received a real Gitea DOWN notification.
- Gotify and Uptime Kuma remained operational.
- 01:14:40 — Operator initiated Gitea recovery.
- 01:14:42 — Guarded systemd startup completed.
- Initial HTTP requests encountered a readiness gap.
- HTTP subsequently returned 200.
- Kuma detected UP and Gotify received recovery notification.

## Verification

- Gitea pre-start SD storage guard passed during recovery.
- Existing Gitea repository remained accessible.
- Failure and recovery appeared in monitoring.
- Both notifications arrived through the dedicated
  ARM Uptime Kuma Gotify application.

## Measurements and limitations

Time from fault injection to recovery initiation:
3 minutes, 22 seconds.

This is not a measured MTTR or exact alerting latency.
The exercise demonstrates service-level monitoring.
Kuma and Gotify currently share the management host,
so complete R5C failure is not independently monitored.
