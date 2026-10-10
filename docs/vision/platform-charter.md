# Platform charter — ARM-first, portable DevSecOps platform

**Status:** Approved planning direction (2026-10-10); individual capabilities remain unimplemented until verified.
**Purpose:** Define the destination without overstating today's evidence.

## Mission

Build an ARM-first, security-conscious platform engineering reference architecture that can be rebuilt, operated and defended by another engineer, and later exercised on Proxmox/VMs or other environments. It must demonstrate the complete change, build, supply-chain, delivery, runtime, incident and recovery lifecycles—not merely install infrastructure products.

## Principles

1. **Working evidence over tool count.** Each capability has a failing/negative test, a positive test and durable evidence appropriate to its risk. Never call a proposed control deployed.
2. **One authority for each desired state.** GitHub protected main owns canonical source; Flux reconciles selected Kubernetes application resources; Ansible converges host and out-of-cluster management services; systemd owns guarded service startup; privileged Kubernetes bootstrap stays separate.
3. **Independent recovery root.** A lost R5C, Gitea service, Kubernetes control plane or OpenBao must not make its own recovery impossible. Public Git, trusted bootstrap instructions and encrypted off-device recovery material remain independently accessible.
4. **Build once; promote identities, not rebuilds.** Validate, test and scan the same artifact; preserve OCI digest, record provenance and verify release-policy decisions before promotion.
5. **Untrusted and privileged execution must be separate.** Public/PR CI has no homelab management credential. A future approved operations runner has distinct identity, trusted inputs, bounded commands and audited changes.
6. **Secure defaults, explicit exceptions.** Risk-adjusted progressive enforcement; approved exceptions require owner, evidence, expiry and reassessment. No unbounded permanent waivers.
7. **Portability by interfaces, not lowest-common-denominator technology.** Keep target inventory, artifact identity, configuration and lifecycle contracts stable; permit site-specific adapters. ARM-first is not ARM-only.
8. **Small increments and no split brain.** One active milestone at a time; backlog ideas do not silently expand its scope. PR checks may be portable, simulated or physical-lab required, and those distinctions must remain visible.
9. **Operational transparency.** Logs/metrics/security findings should answer who changed what, which digest runs, why it was allowed, what failed and how to restore it.
10. **Human-maintainable delivery.** Choose Bash for short CLI glue, Python for structured logic, Ansible for convergence, Flux for app reconciliation, and dedicated testing for policy. Prefer simple interfaces over clever frameworks.

## Current implemented baseline (as of charter adoption)

- GitHub canonical with protected main and CI; Gitea private one-way mirror; independent R5C.
- Guarded SD-backed management services and Ansible-managed service lifecycle.
- Hosted and physical ARM64 validation; immutable image built/tested/scanned once and published to GHCR.
- Exact digest replication and retrieval from Gitea OCI.
- Scoped Kubernetes identity, immutable deployment and controlled failed-rollout recovery.
- Hardened Flux with a namespace-scoped application reconciler; drift, Git propagation and suspend/resume proven.

This baseline **does not** prove a fresh-metal rebuild, production-like secrets lifecycle, artifact attestations, complete admission policy, runtime security, dependable 4h/1h recovery, or service-level observability. See [existing evidence](../interview/engineering-evidence.md), [objective register](../planning/objectives.md) and [roadmap](../roadmap.md).

## Target delivery streams

| Stream | Authority | Target evidence |
|---|---|---|
| Source governance and developer workflows | Protected GitHub | Enforced approvals, reproducible and policy-checked changes |
| Portable CI and testing | GitHub Actions; restricted Gitea validation | Unit/integration, security and platform contract checks without the lab |
| Build and artifact supply chain | Build/publish jobs and registries | SBOM, provenance, digest identity, signatures, verified promotion |
| Kubernetes applications | Flux plus scoped ServiceAccounts | Drift correction, policy enforcement, readiness and rollback |
| Host and management plane | Ansible plus systemd | Safe idempotence, startup gates, credential-separated maintenance |
| Local approved operations | Separate trusted operations runner (future) | Signed/approved inputs, bounded changes, audit and recovery independence |
| Runtime reliability and security | Metrics/logs/alerts, security sensors and operator | Actionable incidents, containment and evidence |
| Secrets/identity | OpenBao for routine use, external recovery trust root | Bootstrap, rotation, revocation, TTL and compromise testing |
| Recovery | Off-device encrypted backups and rebuild tooling | Blank-host rebuild, isolated restore, independently verified recovery objectives |
| Portability and developer experience | Target contracts and golden paths | Second environment, comprehensible docs and reproducible onboarding |

## Lab/off-lab acceptance tiers

- **P — Portable:** GitHub-hosted tests, schemas, source lint, mock API tests, manifest renders, deterministic fixtures; never claim live-host success.
- **S — Simulated:** throwaway VM/container/ephemeral Kubernetes integration and negative tests; document equivalence gaps.
- **H — Hardware/site:** real R5C/SD/systemd/network/physical ARM/Kubernetes behavior and controlled failures. Only H can complete objectives that explicitly require physical state.

Record which tier is required for each acceptance criterion. Work may be contributed and reviewed remotely, but live-impacting milestones remain open until their H gates pass.

## Recovery SLO planning targets (not achieved)

**Chosen design targets:** RTO **4 hours** and RPO **1 hour**. These are aspirational engineering constraints, not measured guarantees or availability SLAs. The reference recovery clock starts at incident declaration and ends when agreed critical capabilities pass recovery checks. RPO bounds acceptable *recoverable* loss of classified mutable state relative to the event; a backup schedule alone does not prove RPO.

Initial critical-scope proposal: Git/mirror recoverability, Gitea repository and OCI package state, identities and config needed for management services, and essential management control access. Classify Uptime Kuma history, transient CI logs, metrics and caches separately. Cluster etcd and workload data require their own scope and restore plan. Final data classification, dependency ordering, spare hardware and network assumptions are an implementation gate, not already decided.

4h/1h implies at least hourly-enough consistent capture with margin, off-device redundancy, key availability, fast rebuild/replacement access and rehearsed runbooks. A 4h restore cannot be assumed if spare hardware is unavailable or restoration depends on a failed local forge.

## Exit definition for the overall program

A second operator, starting with Git and protected recovery material, can provision a supported target, validate trust and release policies, deliver a signed/provenance-linked image by digest, observe a controlled failure, recover service and rebuild lost state within measured objectives. Every claim points to tests, runbooks, run IDs or a documented limitation.

## Non-goals for this planning PR

No new runtime components, runner privilege, secret publication, CI enforcement switch, artifact signing or actual live-environment mutations. No forced Gitea-to-Forgejo migration, Terraform dependency, Backstage installation or wholesale Bash rewrite.
