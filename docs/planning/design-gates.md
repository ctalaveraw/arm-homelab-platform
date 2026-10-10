# Architecture design decisions and implementation gates

**Recorded:** 2026-10-10. These design choices are approved direction; verification is future work.

| Gate | Adopted decision | Implication |
|---|---|---|
| DG-01 | ARM-first, portable to Proxmox and other targets | Target-specific adapters; no accidental R5C-only contract in shared policy |
| DG-02 | Dedicated restricted, approval-gated local operations runner | Do not add deploy/admin credentials to existing untrusted validation runner |
| DG-03 | Protected PR → trusted validation → approved Ansible convergence | No unattended infrastructure apply on every main merge by default |
| DG-04 | Independent encrypted recovery bundle; OpenBao for routine secrets | No circular dependence on OpenBao or Gitea for day-zero recovery |
| DG-05 | Risk-based staged DevSecOps enforcement and expiring exceptions | Document threshold, owner, expiry, compensating controls, measured rollout |
| DG-06 | RTO 4 hours; RPO 1 hour **targets** | Recovery state classification, hourly-consistent copies and timed isolated rehearsal required |
| DG-07 | Forgejo and developer portal: evaluate now, defer implementation | Neither becomes prerequisite to observability, restore or core delivery |
| DG-08 | Planning PR = backlog + vision + roadmap + ADRs | Documentation-only; no live behavior, secrets or enforcement altered |

## Follow-up implementation gates, not blockers to this planning PR

1. **Recovery scope:** decide tiered critical services/data (Gitea database/repositories, OCI packages, runner identity, PKI, kubeadm/etcd, monitoring history); define incident start/stop and what 4h/1h specifically cover.
2. **Recovery medium and hardware:** identify backup destination(s), credentials and encryption-key escrow, spare ARM target or VM equivalent, network/DNS prerequisites, offsite reachability and resource/cost ceilings; prove loss of R5C and/or SD is recoverable.
3. **PKI bootstrap:** define CA ownership, issuer access, X.509 deployer identity generation, certificate renewal/revocation, kubeadm admin/etcd/Flux bootstrap assets, restoration after key compromise. Never store cleartext private keys in public Git.
4. **Operations runner identity:** choose separate approved repository/workflow source, runner executor and isolated host, ephemeral/job-scoped credentials, human approver identity, PR-origin protection, concurrency locks, audit retention and break-glass path. The validation runner remains credential-free.
5. **Delivery promotion:** choose how a verified digest enters Git (separate bot PR versus human promotion) and how signed attestations are independently verified before publication and admission. Flux remains application-state owner.
6. **Runtime controls:** define admission rollout sequence, policy exception format, test namespaces, CPU/memory budget on Pis, egress requirements and bootstrap allowlist; fail closed without breaking cluster recovery.
7. **Config transport:** classify `.env` keys and paths; decide secure file injection versus app-specific env support; define ownership, backup/restore, trust CA and redaction rules.
8. **APT proxy:** complete source ACL validation and prove optional cache bypass before using it in the fourth-Pi bootstrap. Management HTTPS is separate work.
9. **Forgejo/portal:** assess real export/import compatibility and rollback in an isolated environment; trigger portal proof only when multiple services/personas justify it.
10. **Portability:** define second-target minimum fidelity (Proxmox VM plus Terraform provisioning versus physical second ARM host), inventory abstractions, providers and secret boundaries.

## Decision/change control

Treat design commitments as accepted direction but revisit via ADR when evidence shows that the selected approach is unsafe or impractical. Each workstream milestone needs an explicit threat/acceptance scope; do not use planning-ticket completion as evidence that the runtime control exists.
