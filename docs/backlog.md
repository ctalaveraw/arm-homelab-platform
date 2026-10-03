# Platform Engineering Backlog

## Working Agreement

- One active implementation milestone at a time.
- New ideas enter the backlog, not the current sprint.
- Each completed milestone requires verification.
- Record architectural decisions in docs/adr/.
- Record implementation evidence in docs/interview/.
- Reprioritize when interview requirements change.

## NOW — Delivery Foundation

- [x] PLAT-001: Public GitHub bootstrap/recovery remote
- [x] PLAT-002: Ansible inventory, preflight and common role
- [x] PLAT-003: Ansible-managed Docker host (existing R5C)
- [x] PLAT-004: Gitea with persistent storage
- [ ] PLAT-005: Gotify notifications
- [ ] PLAT-006: Gitea Actions runner
- [ ] PLAT-007: Container registry
- [ ] PLAT-008: CI lint/test/build/scan
- [ ] PLAT-009: Helm deployment pipeline
- [ ] PLAT-010: Incident and rollback exercise

## NEXT — Platform Maturity

- [ ] PLAT-011: Flux GitOps reconciliation
- [ ] PLAT-012: Prometheus and Grafana
- [ ] PLAT-013: Runtime alerting to Gotify
- [ ] PLAT-014: Ansible bootstrap of fourth Pi
- [ ] PLAT-015: Reproducible kubeadm node join
- [ ] PLAT-016: OpenBao secrets integration
- [ ] PLAT-017: Gitea backup/restore validation
- [ ] PLAT-018: Management plane DR exercise

## FUTURE — Independent Projects

- [ ] AWS-001: Ephemeral hybrid access via Terraform
- [ ] AWS-002: Terraform AWS networking baseline
- [ ] AWS-003: IAM and infrastructure security
- [ ] AWS-004: AWS CI/CD integration
- [ ] SEC-001: Container supply-chain controls
- [ ] OPS-001: SLO and incident response lab
- [ ] OPS-002: Automated recovery exercises
- [ ] AI-001: AI infrastructure deployment lab

- [ ] OPS-003: Reproducible interactive Zsh environment
  - Dependencies: zsh, fzf, zoxide, git-delta
  - Source: /srv/_local/scripts/bootstrap_shell.sh
  - Arguments: --human --add-root-shell
  - Review root-shell changes before execution.
  - Keep optional; do not block infrastructure bootstrap.

- [ ] OPS-004: Add Gitea HTTP readiness checks and HTTPS before broader access.

## Parking Lot

Ideas go here until formally prioritized.

Do not expand the active sprint merely because
a new technology looks interesting.
