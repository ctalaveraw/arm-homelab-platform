# ADR-0010: Separate trusted local operations from repository validation

Status: Accepted for target architecture
Date: 2026-10-10

## Context

The current Gitea Actions runner runs ARM64 validation on the R5C without a Docker host socket, privileged mode, cluster credentials or deployment credentials. GitHub remains canonical and mirrors to Gitea. Giving that validation runner a privileged Ansible identity would create a path from repository changes into management authority, including risk from untrusted workflows and compromised dependencies.

Normal Kubernetes application state is already owned by Flux. A second workflow that directly applies the same manifests would create competing writers.

## Decision

Create a **separate, restricted local operations execution boundary** when automation is introduced. It consumes only trusted, reviewed, pinned sources and requires explicit authorized approval for state-changing host operations. It must not execute arbitrary mirrored PR code with sensitive credentials.

- Gitea Actions: approved trigger, bounded job graph, audit and results.
- Ansible: desired-state host/package/systemd/Compose convergence with idempotence and explicit inventory.
- Repository scripts/Python: validation, API-specific commands, pre/post checks, safe retry and evidence capture.
- Flux: sole routine reconciler of its Kubernetes application inventory.
- Privileged cluster bootstrap: separate, explicitly authorized admin recovery procedure; not a GitOps self-management loophole.

Separate machine/OS identity and filesystem/credential boundary preferred; a second runner registration alone on the same unisolated host does not provide full isolation. Default deny for host daemon socket, direct root, unattended writes and production credentials exposed to PR contexts. Define allowlisted playbooks/arguments, approver and audit event, exclusive execution locks, timeout, bounded rollback and denied-path tests before activation.

Gitea-dependent jobs are **not** the recovery root for Gitea or the R5C. Ansible must remain independently runnable using verified off-device source and recovery credentials.

## Consequences

Benefits: narrow operational authority, explicit approvals and inspectable state. Costs: another runner lifecycle, credential management and bootstrap/recovery procedure. Automatic on-merge infrastructure convergence is deferred. Existing validation runner and Flux authority are unchanged by this ADR.

## Validation required before production-like use

Prove an untrusted PR cannot gain operations credentials, a deliberately unauthorized playbook/host is denied, expired approval/token fails, concurrent conflicting jobs cannot run, operations events have actor/revision/result identity, and a dead Gitea can still be recovered without its runner.
