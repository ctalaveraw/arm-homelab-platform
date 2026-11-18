# Platform charter

Approved direction: 2026-10-10. Current deployment reviewed: 2026-11-18.

## Mission

Build an ARM64 platform that another operator can configure, deploy, diagnose and recover using this repository and protected recovery material. A second environment, such as Proxmox, should be able to reuse the same source, artifact and deployment contracts.

## Current implemented baseline

- GitHub owns protected source; Forgejo provides the local pull mirror, repository-scoped validation and OCI distribution.
- The R5C manages services independently of Kubernetes. Ansible configures the host; systemd checks SD storage before Compose startup.
- GitHub and physical ARM64 workers validate the repository. CI builds, tests and scans one image, verifies its transfer and publishes it to GHCR.
- Flux reconciles the application namespace from GitHub. Scoped deployment access, drift correction, suspend/resume and failed-rollout recovery have been tested.
- Forgejo migration checks passed for source parity, SSH, OCI retrieval and manual/push native workflows. Kuma now targets its health endpoint.
- Host, Kubernetes API and Flux telemetry are deployed. Wider service coverage, alerts, restore and blank-host reconstruction remain open.

Use the [architecture](../architecture/overview.md), [migration record](../runbooks/gitea-to-forgejo.md) and [evidence ledger](../interview/engineering-evidence.md) for implementation details.

## Operating principles

1. Give each resource one owner: GitHub for source, Flux for application desired state, Ansible for host configuration and systemd for service startup.
2. Keep recovery source, credentials and decryption keys accessible when the local forge, cluster or secret service is down.
3. Test and scan the image that will be published. Preserve its digest through replication and deployment.
4. Keep public PR execution separate from privileged operations. A future operations runner needs its own identity, reviewed inputs, approval, timeouts and audit records.
5. Record security exceptions with an owner, reason, scope and expiry. Test both allowed and denied operations.
6. Add target-specific inventory and adapters where required. Keep shared artifact and interface contracts consistent.
7. Finish one milestone before starting another. Record whether a result came from portable tests, simulation or the physical lab.
8. Choose small scripts for command orchestration, Python for structured logic, Ansible for host configuration and Flux for application reconciliation.

## Target delivery streams

| Stream | Owner | Required result |
| --- | --- | --- |
| Source and CI | GitHub / restricted Forgejo validation | Reviewed changes and reproducible checks |
| Artifact supply chain | Build/publish jobs and registries | SBOM, provenance, signatures and verified digest promotion |
| Kubernetes applications | Flux / scoped ServiceAccounts | Policy enforcement, drift correction, readiness and rollback |
| Host services | Ansible / systemd | Repeatable configuration, storage checks and controlled maintenance |
| Approved operations | Separate future operations runner | Limited credentials, approvals and audit records |
| Reliability and security | Monitoring, logs and operator procedures | Actionable alerts, incident response and containment |
| Secrets and identity | Planned OpenBao / independent recovery material | Bootstrap, expiry, rotation, revocation and recovery |
| Recovery | Off-device encrypted backups / rebuild tooling | Tested restore and measured recovery time/data loss |
| Portability and onboarding | Environment contracts and runbooks | A working second environment and repeatable contributor setup |

The [objective register](../planning/objectives.md) defines individual work items and dependencies.

## Lab/off-lab acceptance tiers

| Tier | Environment | Examples |
| --- | --- | --- |
| P — Portable | Hosted CI or developer machine | Lint, schemas, mocked APIs, manifest rendering |
| S — Simulated | Disposable VM, container or cluster | Integration tests and controlled failures |
| H — Hardware/site | Physical lab | SD mounts, boot order, network paths and service recovery |

Each objective states its required tier. Record simulation gaps explicitly; physical checks still require a lab operator.

## Recovery SLO planning targets (not achieved)

The targets are a four-hour recovery time objective (RTO) and a one-hour recovery point objective (RPO). Neither has been measured in a full recovery drill.

Start the recovery clock at incident declaration and stop it when the agreed critical services pass their checks. RPO measures recoverable data loss relative to the incident.

Classify Forgejo repositories/packages, service identities, configuration and management access as candidate critical state. Classify monitoring history, transient CI logs and caches separately. Kubernetes etcd and workload data need their own capture and restore procedures.

Meeting these targets requires consistent capture with enough margin, off-device copies, available keys, replacement hardware and rehearsed rebuild/restore steps. Final service scope, backup media, key custody and dependency order are open decisions.

## Exit definition for the overall program

A second operator can start with Git and protected recovery material, configure a supported target, verify release policy, deploy an image by digest, diagnose a controlled failure and restore service within measured recovery objectives. The [roadmap](../roadmap.md) and [backlog](../backlog.md) track that work.
