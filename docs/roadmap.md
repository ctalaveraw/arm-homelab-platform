# Platform engineering roadmap

Updated 2026-11-18. Forgejo is live on LAN HTTP/3000 and SSH/2223; source parity, OCI retrieval, native CI and availability passed. The old Gitea state is retained for rollback.

Public Zulip is also deployed on the controller: healthy app/connector probes,
public HTTPS, organization creation and owner login passed. OPS-020 tracks the
remaining functional, capacity/isolation and recovery checks in its runbook.

## Current objective

Complete host, Kubernetes and service observability, then test alerts, node reconstruction, secrets and restore. Release policy and privileged operations follow those foundations. See the [charter](vision/platform-charter.md), [design decisions](planning/design-gates.md) and [objective register](planning/objectives.md).

## M0 — Bootstrap and discovery

Complete: repository, host baseline, storage decisions and external GitHub recovery source recorded.

## M1 — Management host as code

Implemented on the existing R5C: Ansible inventory, preflight, host packages, Docker/Compose and service lifecycle. Repeat runs converged without changes. Fresh-host reconstruction is untested.

## M2 — Development infrastructure

Operational: Forgejo, repository-scoped runner, Gotify, Kuma and APT-Cacher-NG use guarded SD state. GitHub owns source and protected `main`; Forgejo mirrors it and validates trusted main-branch workflows on the physical R5C.

The 2026-11-18 migration passed HTTP health, SSH, source parity, OCI retrieval and manual/mirrored-push CI. Kuma's target is now `/api/healthz`. Review [retained legacy state and remaining checks](runbooks/gitea-to-forgejo.md#9-acceptance-and-retention) before retiring Gitea backups. The original Gitea work remains in its dated sprint records.

Public chat uses a separate guarded controller project with seven containers and
no published host ports. OUTER/INNER retain their network roles. See the
[service map](architecture/deployment-standards.md) and
[Zulip operator runbook](runbooks/zulip-controller.md).

## M3 — Application delivery

Complete:

- ARM64 image build and non-root HTTP runtime checks.
- Dockerfile validation, Trivy scan and isolated image transfer with checksum/image-ID verification.
- GHCR publication from a job with registry write permission.
- Digest-preserving OCI distribution and independent retrieval; the current local package is on Forgejo.
- Kubernetes deployment by digest, scoped X.509 access, rollout and endpoint verification.

The first verified publication remains the migration's transferred artifact:

```text
commit: 1ddd76c14a35f974d06dbd1ed7e3c4c14475c92d
digest: sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e
```

Details: [application CI](sprints/08-application-delivery-foundation.md), [OCI distribution](sprints/09-dual-oci-distribution.md) and [Kubernetes delivery](sprints/10-kubernetes-delivery.md).

## M4 — Operational evidence

Completed exercises cover the original Gitea outage and Gotify DOWN/UP notifications, CI publication failures, tampered image handoffs, and a failed Kubernetes rollout with service continuity and rollback.

The Gitea notification drill is historical. Delivery of alerts from the updated Forgejo monitor has not been retested. Kubernetes recovery is documented in the [incident](incidents/2026-10-09-platform-hello-failed-rollout.md) and [runbook](runbooks/kubernetes-deployment-rollback.md).

## M5 — GitOps

Complete: Flux 2.9.6 source and Kustomize controllers reconcile the application from GitHub. Cross-namespace references and remote bases are disabled; application reconciliation uses a namespace-scoped identity and a restricted default identity.

Drift correction, Git changes and suspend/resume behavior were tested. Namespace/RBAC/controller bootstrap stays with the administrator. The scoped X.509 deployment identity remains available for recovery. See [Sprint 12](sprints/12-flux-gitops.md).

## M6 — Observable, reproducible and recoverable operations (active roadmap)

| Work | Current status / next check |
| --- | --- |
| PLAT-012 — Metrics | Eight targets/five dashboards accepted previously; latest inventory showed Prometheus/Grafana stopped. Capacity review, monitoring resumption, workload-state coverage, service probes, isolation, outage and reboot checks remain open. |
| PLAT-013 — Gotify runtime alerts | Define thresholds, routing, deduplication, recovery and missing-signal tests. |
| PLAT-014/015 — Fourth Pi / node join | Implement blank-device bootstrap, host convergence and repeatable kubeadm join; verify APT cache bypass and storage/network failures. |
| PLAT-016 — OpenBao | Establish independent key/PKI recovery, trusted management HTTPS and short-lived routine credentials. |
| PLAT-017/018 — Backup / disaster recovery | Capture consistent off-device state, restore in isolation and reconstruct without the local forge or secret service. |
| OPS-020 — Public chat | Startup, HTTPS and organization/owner login accepted. Invitation policy/delivery, messages/uploads, external/native clients, capacity/isolation and recovery remain pending. |

The recovery targets are four hours RTO and one hour RPO for a defined critical scope. They remain unmeasured. The current Ansible preflight expects a booted ARM64 host and mounted labeled SD; blank-device provisioning is separate work.

See [host telemetry](sprints/13-observability-host-foundation.md), [Kubernetes/Flux telemetry](sprints/14-kubernetes-flux-telemetry.md) and the [backlog](backlog.md).

## M7 — Secure delivery and continuous assurance (planned)

Add threat modeling, workflow/dependency policy, SBOM, provenance, digest signatures and verified promotion PRs. Extend Kubernetes admission, workload/network policy and incident response after the recovery foundation is tested.

Roll controls out in observe, warn, block and verify stages. Record exception owners and expiry. Work items: SEC-001..031, REL-001..006 and CI-003..011.

## M8 — Independent trusted local operations (planned)

Use a separate approved operations runner with limited credentials, reviewed playbooks, locks, timeouts and audit records. Ansible manages hosts; Flux continues to reconcile applications. Recovery must work while Forgejo is unavailable.

Work items: OPS-008/009/015, ENG-001..005 and CI-006/009.

## M9 — Portability, development experience and portfolio capstone (future/evaluate)

Test a second environment through explicit target contracts, optionally using Terraform/Proxmox. Evaluate a portal only when several services or users need templates and self-service workflows.

Contributors should be able to run portable checks off-lab and hand physical tests to a named operator. Review the documentation with a reader who has no chat history. Work items: PORT-001/002/004/005, DX-001..003, IDP-001/002 and DOC-001/002.

## Scope discipline and acceptance

The objective register contains 94 work items with individual dependencies and test tiers. Work proceeds one milestone at a time. Record portable, simulated and physical results separately; a completed runbook does not close unperformed site tests.

## Sprint cadence

Explain the mechanism, implement a focused change, verify it, record the result and submit it for review. Include failure testing and a short knowledge check where they help validate the milestone.
