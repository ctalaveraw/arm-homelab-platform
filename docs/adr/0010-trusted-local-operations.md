# ADR-0010: Separate trusted local operations from repository validation

Status: Accepted for target architecture
Date: 2026-10-10

## Context

The restricted ARM64 validation runner has no Docker host socket, privileged mode, cluster credentials or deployment credentials. Forgejo manual and mirrored-push validation passed under this configuration on 2026-11-18; see [ADR-0015](0015-forgejo-and-controller-ingress.md). GitHub remains canonical, with a private one-way Forgejo mirror as the destination. Giving that validation runner a privileged Ansible identity would create a path from repository changes into management authority, including risk from untrusted workflows and compromised dependencies.

Normal Kubernetes application state is already owned by Flux. A second workflow that directly applies the same manifests would create competing writers.

## Decision

Create a **separate, restricted local operations execution boundary** when automation is introduced. It consumes only trusted, reviewed, pinned sources and requires explicit authorized approval for state-changing host operations. It must not execute arbitrary mirrored PR code with sensitive credentials.

- Forgejo Actions: approved trigger, bounded job graph, audit and results.
- Ansible: desired-state host/package/systemd/Compose convergence with idempotence and explicit inventory.
- Repository helpers: validation, API commands, pre/post checks, safe retry and evidence capture.
- Flux: sole routine reconciler of its Kubernetes application inventory.
- Privileged cluster bootstrap: separate, explicitly authorized admin recovery procedure; not a GitOps self-management loophole.

Separate machine/OS identity and filesystem/credential boundary preferred; a second runner registration alone on the same unisolated host does not provide full isolation. Default deny for host daemon socket, direct root, unattended writes and production credentials exposed to PR contexts. Define allowlisted playbooks/arguments, approver and audit event, exclusive execution locks, timeout, bounded rollback and denied-path tests before activation.

Forgejo and R5C recovery must run independently of Forgejo jobs. Ansible must remain independently runnable using verified off-device source and recovery credentials. Use the [current runner paths and identity](../runbooks/forgejo-reference-map.md#repository-and-host-paths).

## Consequences

Benefits: narrow operational authority, explicit approvals and inspectable state. Costs: another runner lifecycle, credential management and bootstrap/recovery procedure. Automatic on-merge infrastructure convergence is deferred. Existing validation runner and Flux authority are unchanged by this ADR.

## Validation required before production-like use

Prove an untrusted PR cannot gain operations credentials, a deliberately unauthorized playbook/host is denied, expired approval/token fails, concurrent conflicting jobs cannot run, operations events have actor/revision/result identity, and an unavailable Forgejo can still be recovered without its runner.
