# Platform Engineering Roadmap

## Current Objective

Create one reproducible management plane capable
of delivering an application into an existing
upstream Kubernetes cluster.

## M0 — Bootstrap and Discovery

Status: Complete — bootstrap foundation established.

Exit criteria:
- Repository initialized.
- Brownfield baseline captured.
- Storage decisions documented.
- External GitHub remote verified.

## M1 — Management Host as Code

Status: Implemented on existing R5C; fresh-host rebuild untested.

Exit criteria:
- Ansible inventory exists.
- Common host role executes.
- Docker/Compose installation automated.
- Playbooks verified through repeated execution.

## M2 — Development Infrastructure

Exit criteria:
- Gitea operational.
- Gotify operational.
- Runner accepts jobs.
- Persistent storage documented.
- Critical mount dependencies enforced.

## M3 — Application Delivery

Exit criteria:
- Application builds for ARM64.
- CI validates application and Helm chart.
- Security scan executes.
- Image is published.
- Helm deploys into existing Kubernetes.
- Endpoint and rollout verified.

## M4 — Operational Evidence

Exit criteria:
- A controlled deployment failure is introduced.
- Failure is detected.
- Recovery or rollback is demonstrated.
- Incident report and runbook are committed.

## M5 — GitOps

Introduce Flux and migrate deployment ownership
from push-based CI/CD to pull-based reconciliation.

## M6 — Operational Maturity

Observability, node reconstruction, secrets
management, backup validation and disaster recovery.

## Sprint Cadence

Target: 3–7 focused hours weekly.

Each working session:
1. Orient.
2. Understand.
3. Implement.
4. Verify.
5. Document.
6. Commit.
7. Complete a short knowledge gate.

A milestone is completed through evidence,
not simply because the software was installed.
