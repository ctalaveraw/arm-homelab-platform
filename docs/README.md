# Documentation

The architecture, CI and runbooks describe current operation. Sprint, incident and benchmark records describe the dated deployment they tested.

## Current operation

- [Architecture](architecture/overview.md): hosts, source ownership, storage, ingress and deployment.
- [Deployment standards and service map](architecture/deployment-standards.md): names, manifest/overlay rules, playbooks, lifecycle owners and documented gaps.
- [CI and OCI distribution](ci.md): workflows, runner permissions, mirroring, publication and registry helpers.
- [Forgejo names, paths and clients](runbooks/forgejo-reference-map.md): current URLs, account owner, files and retained legacy references.
- [Gitea to Forgejo migration](runbooks/gitea-to-forgejo.md): accepted migration results, reusable procedure and rollback.
- [Domain ingress](runbooks/domain-ingress.md): public chat and private Forgejo access.
- [Cloudflare Tunnel](runbooks/cloudflared.md): token setup, DNS, activation and withdrawal.
- [Controller public ingress](runbooks/controller-public-ingress.md): Caddy, tunnel and application networks.
- [Controller Zulip](runbooks/zulip-controller.md): accepted/pending checks, routine operations, diagnostics, configuration and recovery.
- [Separate Zulip organizations](runbooks/zulip-organizations.md): certificate checks, subdomain migration, independent organization creation and address rollback.
- [Host metrics](runbooks/observability-host-metrics.md): exporter and dashboard operations.
- [Kubernetes and Flux telemetry](runbooks/kubernetes-flux-telemetry.md): observer credentials, API-proxy scraping and failure handling.
- [Application deployment and rollback](runbooks/kubernetes-deployment-rollback.md): the scoped deployment helper and recovery procedure.

Forgejo is live at `http://git.lab.home.arpa:3000/` with SSH/2223. Source parity, full OCI retrieval and manual/push native CI passed. Kuma's monitor now uses `/api/healthz`. The [migration record](runbooks/gitea-to-forgejo.md) holds the revisions, digest and checkpoints.

## Planning and status

- [Roadmap](roadmap.md): milestone progress and order.
- [Backlog](backlog.md): completed and open work.
- [Objective register](planning/objectives.md): individual requirements, dependencies and test tiers.
- [Design decisions](planning/design-gates.md): approved choices and implementation requirements.
- [Platform charter](vision/platform-charter.md): purpose, responsibilities and recovery targets.
- [Engineering evidence ledger](interview/engineering-evidence.md): dated implementation and test results.
- [Initial R5C baseline](architecture/r5c-baseline.md): the 2026-10-01 host snapshot.

Public Zulip is deployed: the operator confirmed healthy containers, HTTPS,
organization creation and owner login on 2026-11-18. Its runbook tracks mail
delivery, messages/uploads, external/native clients and recovery as pending.
Prometheus and Grafana were stopped in the latest inventory; their earlier
eight-target/five-dashboard results are historical. Private HTTPS, runtime alerts,
restore, fresh-host reconstruction and wider workload metrics remain open.

## Architecture decisions

- [ADR-0001 — Storage layout](adr/0001-storage-layout.md)
- [ADR-0002 — USB archive decommission](adr/0002-usb-archive-decommission.md)
- [ADR-0003 — Independent management and recovery source](adr/0003-independent-management-plane.md)
- [ADR-0004 — Guarded Compose lifecycle](adr/0004-guarded-compose-lifecycle.md)
- [ADR-0005 — Optional APT cache](adr/0005-optional-package-cache.md)
- [ADR-0006 — Build-once OCI promotion](adr/0006-build-once-oci-promotion.md)
- [ADR-0007 — Digest-pinned Kubernetes pulls](adr/0007-digest-pinned-kubernetes-image-pulls.md)
- [ADR-0008 — Scoped external deployment identity](adr/0008-external-kubernetes-deployer-identity.md)
- [ADR-0009 — Flux reconciliation authority](adr/0009-flux-gitops-trust-boundary.md)
- [ADR-0010 — Separate operations and validation runners](adr/0010-trusted-local-operations.md)
- [ADR-0011 — Recovery material and configuration](adr/0011-recovery-root-and-configuration.md)
- [ADR-0012 — Secondary targets and portal evaluation](adr/0012-portability-and-platform-product.md)
- [ADR-0013 — Security policy and artifact promotion](adr/0013-devsecops-policy-and-promotion.md)
- [ADR-0014 — Kubernetes telemetry observer](adr/0014-kubernetes-telemetry-observer.md)
- [ADR-0015 — Forgejo and controller ingress](adr/0015-forgejo-and-controller-ingress.md)

## Sprint records

- [00 — Discovery](sprints/00-bootstrap.md)
- [01 — Management bootstrap](sprints/01-management-bootstrap.md)
- [02 — Gitea](sprints/02-gitea.md)
- [03 — Gotify](sprints/03-gotify.md)
- [04 — Uptime Kuma](sprints/04-uptime-kuma.md)
- [05 — APT cache](sprints/05-apt-cacher-ng.md)
- [06 — CI foundation](sprints/06-ci-foundation.md)
- [07 — Native Gitea CI](sprints/07-native-gitea-ci.md)
- [08 — Application CI](sprints/08-application-delivery-foundation.md)
- [09 — OCI distribution](sprints/09-dual-oci-distribution.md)
- [10 — Kubernetes delivery](sprints/10-kubernetes-delivery.md)
- [11 — Failed rollout and recovery](sprints/11-deployment-failure-rollback.md)
- [12 — Flux](sprints/12-flux-gitops.md)
- [13 — Host metrics](sprints/13-observability-host-foundation.md)
- [14 — Kubernetes/Flux telemetry](sprints/14-kubernetes-flux-telemetry.md)

## Incidents and benchmarks

- [USB storage failure](incidents/2026-10-03-usb-storage.md)
- [Controlled Gitea outage](incidents/2026-10-04-gitea-controlled-outage.md)
- [Controlled Kubernetes rollout failure](incidents/2026-10-09-platform-hello-failed-rollout.md)
- [APT cache benchmark](benchmarks/2026-10-04-apt-cacher-ng.md)

Screenshots under `docs/evidence/` retain their original service names.
