# ADR-0014: Out-of-Cluster, Read-Only Kubernetes Telemetry Observer

Status: Accepted for the PLAT-012 implementation
Date: 2026-10-16

## Context

The independent NanoPi R5C runs Prometheus outside the kubeadm cluster. Direct R5C-to-Pod (`10.244.0.0/16`) access and Kubernetes Service VIP (`10.96.0.1`) access were not reachable in G3C network discovery, although the control-plane API at `10.0.0.5:6443` was reachable. Moving Prometheus into the cluster would couple monitoring availability to the system being observed.

ADR-0009 already separates privileged Flux installation/bootstrap from namespace-scoped application reconciliation. Monitoring must not silently grant Flux, a public Git commit, or the R5C monitoring client administrator authority.

## Decision

- Keep Prometheus and Grafana on the independently managed R5C under Ansible, systemd and fail-closed SD-backed Compose guards.
- Use the existing Kubernetes API server HTTPS endpoint on `10.0.0.5:6443` for the API server's own `/metrics` and for API-mediated proxying of the two Flux controller metrics Services. Do not require direct routing to Pod IPs or the Service CIDR from R5C.
- Keep two separately named, metrics-only ClusterIP Services for Flux source-controller and kustomize-controller, exposed on their existing metrics ports without broadening the controllers' ordinary application authority.
- Install the **observer RBAC** and metrics Services in an isolated, administrator-approved bootstrap Kustomize entrypoint, outside application GitOps reconciliation. Restrict allowed nonresource and resource URLs to the exact metrics paths; do not permit list/get of Secrets, Nodes, Deployments or arbitrary Services, Pod proxying, RBAC modifications or workload mutations.
- Authenticate as `CN=platform-observer` with a dedicated client X.509 certificate signed by the cluster CA, distinct from deployer and kubeadm credentials. The local original key remains protected; Ansible provisions scoped read-only copies into a dedicated Prometheus runtime group with read-only bind mounting.
- Preserve Prometheus UID/GID `65534:65534`, supplemental GID `29012`, 384 MiB memory cap, and existing SD state and retention. Limit expensive high-cardinality metrics at ingest; record both `scrape_samples_scraped` and `scrape_samples_post_metric_relabeling` when discussing dropped data.

## Operational consequences

The API endpoint is now a **single monitoring access path** for all three Kubernetes/Flux targets. Proxy failure or API outage can make several jobs fail simultaneously; independent Pi node exporters provide a separate host signal, not an alternative Kubernetes API path. Do not infer Flux health from a successful Prometheus scrape alone. Missing Flux Ready-condition series mean *unknown / unavailable*, never ready, zero failures or healthy.

Client-certificate enrollment requires an explicit CSR approval gate and immediate capture of the issued certificate: an earlier approved CSR disappeared before its certificate was retrieved. The verified observer certificate expires **2027-01-12 03:15:36 UTC**; rotation, short-lived identity renewal, and revocation must be documented and rehearsed rather than assumed automatic.

The network path and authorization were demonstrated. Firewall isolation for unauthenticated Node Exporter TCP/9100 and a full reboot/recovery exercise remain unproven. Runtime alert routing belongs to PLAT-013, and broader Kubernetes object-state/workload metrics are not implied by this decision.

## Rejected alternatives

- Deploy monitoring exclusively in the cluster: loses the independent observer's availability during cluster failure.
- Expose Flux metrics using LAN-facing NodePorts or broad Pod-CIDR routing: expands network exposure and policy complexity.
- Reuse cluster-admin/deployer kubeconfig or grant broad proxy rights: breaks least privilege and separation of duties.
- Add observer bootstrap to the ordinary Flux application Kustomization: risks privilege escalation through public application Git.

## Verification and related records

- Live X.509 allow/deny tests covered API metrics, both Flux metrics paths, unauthorized Services/Pods, Secrets/Nodes/Deployments and forbidden mutations.
- G2d acceptance showed eight live scrape targets, including the API and two Flux jobs. G4 acceptance repeated eight healthy, fresh scrape targets, both management playbooks with `changed=0`, and checked container bounds and Grafana's authenticated five-dashboard catalog.
- [Monitoring runbook](../runbooks/kubernetes-flux-telemetry.md), [Sprint 14](../sprints/14-kubernetes-flux-telemetry.md), [ADR-0009](0009-flux-gitops-trust-boundary.md).
