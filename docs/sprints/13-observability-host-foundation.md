# Sprint 13 — PLAT-012 Physical Host Observability Foundation

Date: 2026-10-11  
Status: Physical host foundation delivered; PLAT-012 milestone remains open.

## Objective

Collect actionable R5C and physical Kubernetes-node metrics from an independent management plane without modifying the cluster's Flux ownership, granting Kubernetes credentials to CI, or exhausting two 906 MiB Pi workers.

## Implemented

- Prometheus v3.15.0, non-root, read-only container, 384 MiB memory and 128-PID limits, guarded SD-backed state and systemd-controlled lifecycle; API reachable only on R5C loopback TCP/9090.
- TSDB capped at 48 hours and 512MB; 30-second scrape and rule evaluation intervals.
- Grafana 13.2.2, non-root, 768 MiB memory and 256-PID limits, guarded SD-backed storage, provisioned Prometheus source, platform/R5C/Pi dashboards and restricted plugin loading; LAN TCP/3300.
- Pinned Node Exporter v1.12.1 on R5C and Pis with SHA-256-verified archive, dedicated unprivileged identity and native systemd isolation; 96 MiB R5C and 64 MiB Pi caps.
- R5C filesystem metrics work through minimal `--x` parent/mount ACL grants; native exporter has no access to the Grafana secret.
- Dedicated Pi inventory uses SSH aliases and verified host identities rather than embedding SSH private keys. Ansible deploys one Pi at a time.
- Prometheus jobs: `prometheus`, `r5c`, `pi-nodes`. The Pi job supplies stable `node` and `role` labels.
- Regression coverage and syntax/lint/Compose validation in `scripts/ci/validate.sh`.

## Physical acceptance

| Check | Evidence |
| --- | --- |
| R5C | CPU, RAM, SD capacity and zero filesystem-device-error results received by Prometheus |
| Three Pi targets | `up{job="pi-nodes"}=1` on each host |
| Pi metrics | CPU, RAM, root filesystem and no filesystem-device-error series on all three |
| Host isolation | Dedicated Node Exporter identities; service caps; R5C secret denial test |
| Cluster availability | All three kubelets active after exporter deployment |
| Pi idempotence | `ci-controller-01`, `-02`, `-04`: `ok=14 changed=0 unreachable=0 failed=0` each |
| R5C idempotence | `ok=38 changed=0 unreachable=0 failed=0` |
| CI | Full portable/static validation, including 30 Python tests, passed |
| Code checkpoints | `dfa33e4`, `2b5a1e6`, `9b19672`, `bf0c5aa`, `8a46ceb` |

A transient SSH transport disconnect interrupted one repeat Ansible execution; subsequent SSH and all three-node idempotence runs succeeded. This is not recorded as an exporter or kubelet failure.

## Remaining, explicitly unproven

- Network-segment/firewall restriction for unauthenticated Node Exporter HTTP TCP/9100.
- Kubernetes control-plane metrics, workload object-state signals and Flux controller reconciliation metrics.
- Broader management-service dependencies, blackbox/application health, SD wear/write capacity.
- Negative/failing-scrape evidence, retention/cardinality trends, longer-running resource load budgets and reboot/failure recovery exercises.
- Gotify actionable alert routing belongs to PLAT-013, not this code delivery.

## Operating and recovery notes

Follow the [host metrics runbook](../runbooks/observability-host-metrics.md). Review logs and failure paths without exposing credentials, changing Flux RBAC or bypassing SD storage guards.

## Scope boundary

The main PLAT-012 backlog entry is intentionally still unchecked. This PR proves the physical host-monitoring foundation and prepares subsequent focused PRs for Kubernetes/Flux telemetry, service health and final acceptance.
