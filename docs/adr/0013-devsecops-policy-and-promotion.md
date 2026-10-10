# ADR-0013: Progressive risk-based DevSecOps enforcement and artifact promotion

Status: Accepted for target architecture
Date: 2026-10-10

## Context

CI currently validates source/Compose/Ansible, builds once, tests the image, scans with Trivy, transfers across verified jobs and publishes to GHCR. Same-digest replication to Gitea and Flux reconciliation are proven. Vulnerability scan output and immutable digests do not themselves prove trusted builder identity, SBOM provenance, admission policy or a comprehensive vulnerability response process.

## Decision

Manage security as controls **across** SCM, CI execution, dependencies, build, artifact, promotion, deployment, runtime, incident and recovery streams. Use risk-based staged gates:

- **Observe:** establish findings baseline and false positives without changing operational authority.
- **Warn:** publish findings and expiring exceptions with owner/justification.
- **Block:** fail on agreed high-confidence critical risks, unauthorized provenance/signatures or forbidden deployment configurations, with narrowly approved break-glass procedures.
- **Verify:** inject positive and negative cases and independently confirm enforcement after enablement.

Explicit policy exceptions must have owner, ticket, reason, scope, creation/expiry, compensating controls and review. No blanket permanent suppressions. The existing critical-vulnerability block remains until an intentional approved policy change.

Build once and preserve tested artifact identity. Extend with SBOM, source/build provenance, signature, verification and traceability through digest promotion. Proposed promotion flow: builder publishes verified output → gated digest-specific change to Git desired state → Flux reconciles after PR approval. CI, operations and Flux must not independently race to own Kubernetes application state.

CI and trusted local operations identities are separate. Security scans/attestations must use appropriate tool support and resource budget for ARM; adding redundant scanners without improved coverage is not a goal.

## Acceptance

Demonstrate rejected tampered artifact, untrusted workflow trying to obtain privileged secrets, unacceptable image admission, controlled exception expiry, simulated vulnerable dependency policy, approved immutable digest promotion, and complete trace from Git revision to running digest to alert/incident.
