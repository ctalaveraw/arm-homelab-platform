# Sprint 14 — PLAT-012 Kubernetes API and Flux Telemetry

Status: Kubernetes/Flux telemetry extension accepted through G4.1; documentation/PR closeout in progress. Broader PLAT-012 requirements remain open.
Date: October 2026

## Scope and architecture

Extends [Sprint 13's physical host foundation](13-observability-host-foundation.md) rather than rewriting that historical evidence. The NanoPi R5C continues to host Prometheus/Grafana independently from the three-node kubeadm cluster. It scrapes `10.0.0.5:6443` over authenticated TLS for Kubernetes API server metrics and two Flux controller metrics Services via narrowly authorized API proxy paths. The R5C intentionally does not need access to Pod CIDRs or Kubernetes ClusterIP networking.

The metrics Services, namespace Role/RoleBinding and ClusterRole/ClusterRoleBinding live under `deploy/kubernetes/observability/` as a separate privileged-bootstrap Kustomization, not an application Flux Kustomization. A dedicated `CN=platform-observer` certificate and guarded Ansible runtime copies provide monitoring identity without copying kubeadm/deployer credentials into Prometheus.

## Implemented work

- Added two metrics-only Flux ClusterIP Services and constrained monitoring RBAC, with six exact Kubernetes resources, server dry-run and positive/negative live authorization checks.
- Issued and immediately captured a 90-day observer client certificate after the first approved CSR disappeared before retrieval; verified cluster CA, subject, key pairing and forbidden mutation paths.
- Added three Prometheus HTTPS scrape jobs for Kubernetes API, Flux source-controller and Flux kustomize-controller; retained all existing host jobs. Provisioned a read-only observer bind and supplemental group `29012` while preserving the 384 MiB Prometheus limit.
- Added Kubernetes API (9 panels) and Flux reconciliation (10 panels) dashboards. Corrected host bind-mount configuration directory traversal for Grafana UID `472`; authenticated catalog acceptance found all five dashboards.
- Added regression tests for permissions, RBAC, scrape jobs, guard normalization and dashboard contracts. Canonical CI and Ansible idempotence passed.

## Accepted runtime evidence

- Prometheus: eight active targets healthy — `prometheus` (1), `r5c` (1), `pi-nodes` (3), `kubernetes-apiserver` (1), `flux-source-controller` (1), `flux-kustomize-controller` (1).
- G4 read-only baseline: Kubernetes API 310 retained samples per scrape; Flux source 42 and Flux kustomize 22; 6,590 TSDB head series and 11,317 head chunks (point-in-time values, not capacity guarantees).
- G4 memory snapshot: Prometheus Docker accounting 88.89/384 MiB, Grafana 397.7/768 MiB; Prometheus process RSS 146.9 MiB (different measurement from Docker memory).
- Prometheus and Grafana containers retained their IDs during the G4.1 security/idempotence checks; both Ansible playbooks converged with `changed=0`, no failed tasks. Grafana anonymous catalog access returned HTTP 401; authenticated access returned all five dashboards.
- The observer certificate was valid for more than 30 days in G4 and expires 2027-01-12 03:15:36 UTC.
- 44 tracked Markdown documents and 190 local Markdown paths were inspected at G4; no missing local link paths reported at that baseline.

## Not proved / intentionally deferred

- **No induced production scrape outage or negative network-zone reachability test.** Static safety regressions and live authorization denials do not substitute for a controlled network failure exercise.
- Exporter ports 9100 are unauthenticated within their reachable network boundaries; isolation from untrusted VLANs is not yet independently proven.
- Two Flux Ready-condition expressions returned *no series*. Treat missing as unknown; the panels do not prove zero unhealthy Flux objects.
- Workload object-state exporters, management-service dependency metrics, runtime alert delivery and automatic certificate renewal are not included in this extension.
- The R5C reboot exposed network readiness and source-file permission boot failures. Services were manually recovered, but permanent restart-order recovery is tracked in a **separate PR**; no reboot-resilience claim is made here.
- High-volume/load tests, sustained resource usage, historical incident recovery and disaster restore remain future exercises.

## Relevant paths

- `deploy/kubernetes/observability/`
- `compose/observability/prometheus.yml`
- `compose/observability/grafana/dashboards/kubernetes-api.json`
- `compose/observability/grafana/dashboards/flux-reconciliation.json`
- `ansible/playbooks/07-prometheus.yml`, `ansible/playbooks/08-grafana.yml`
- [Kubernetes/Flux metrics operations runbook](../runbooks/kubernetes-flux-telemetry.md)
- [ADR-0014](../adr/0014-kubernetes-telemetry-observer.md)
