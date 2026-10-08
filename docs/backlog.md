# Platform Engineering Backlog

## Working agreement

- One active delivery milestone at a time.
- New ideas enter the backlog instead of interrupting the current gate.
- A milestone is not complete until implementation **and** verification are recorded.
- Architecture decisions belong in `docs/adr/`.
- Interview-relevant proof belongs in `docs/interview/`.
- Historical sprint/incident records remain historical.
- Delivery gates include a short knowledge check so implementation can be defended conversationally.

## NOW — Kubernetes delivery

- [x] PLAT-001: Public GitHub bootstrap/recovery remote
- [x] PLAT-002: Ansible inventory, preflight and common role
- [x] PLAT-003: Ansible-managed Docker host
- [x] PLAT-004: Gitea with guarded persistent storage
- [x] PLAT-005: Gotify notifications
- [x] PLAT-006: Repository-scoped native Gitea Actions runner and mirrored ARM64 validation
- [x] CI-001: Portable ARM64 repository validation
- [x] GIT-002: One-way GitHub -> Gitea native pull mirror
- [x] OPS-005: Uptime Kuma monitoring and controlled recovery drill
- [ ] OPS-006: APT-Cacher-NG — operational; source ACL verification pending
- [ ] OPS-007: Shared HTTPS for management services

- [x] PLAT-007: First application delivery pipeline
  - [x] ARM64 Hello World application source
  - [x] non-root local runtime acceptance
  - [x] GitHub-hosted ARM64 build + HTTP acceptance
  - [x] Buildx Dockerfile quality check before build job
  - [x] build once and test an explicit image reference
  - [x] Trivy vulnerability + secret scan of the tested image
  - [x] CRITICAL findings block promotion; lower severities remain visible
  - [x] transfer the tested/scanned image across an isolated job boundary
  - [x] verify transfer archive SHA-256
  - [x] verify Docker image ID before and after transfer
  - [x] isolate `packages: write` to the publisher job
  - [x] publish the verified image to GHCR
  - [x] capture immutable registry digest
  - [x] protect GitHub `main` and require CI-backed PR flow
  - [x] strengthen repository validation with Ruff, yamllint and actionlint

- [x] PLAT-008: Dual OCI distribution
  - [x] prove independent pull of the GHCR artifact by digest
  - [x] validate Gitea built-in OCI registry
  - [x] replicate the verified OCI artifact from GHCR into Gitea without rebuilding
  - [x] preserve registry manifest digest across replication
  - [x] prove complete independent retrieval from both registries
  - [x] link the Gitea package to the mirrored source repository
  - [x] encode replication, parity, retrieval and package-link operations in repo scripts

- [x] PLAT-009: Kubernetes delivery pipeline
  - [x] deploy CI-produced image into the existing kubeadm cluster by digest
  - [x] verify running pod image identity against the published digest
  - [x] verify rollout and endpoint
  - [x] establish namespace-scoped deployment RBAC
  - [x] prove positive and negative authorization boundaries
  - [x] authenticate directly from the R5C with a scoped X.509 identity
  - [x] remove SSH and cluster-admin from the routine deployment path
  - [x] add repository-owned deployment and verification interface
  - [x] record engineering evidence and close the delivery milestone
  - [x] keep the first delivery path raw; defer Helm until its abstraction is justified

- [ ] PLAT-010: Deployment failure and rollback exercise

## NEXT — Platform maturity

- [ ] PLAT-011: Flux GitOps reconciliation
- [ ] PLAT-012: Prometheus and Grafana
- [ ] PLAT-013: Runtime alerting to Gotify
- [ ] PLAT-014: Ansible bootstrap of fourth Pi
- [ ] PLAT-015: Reproducible kubeadm node join
- [ ] PLAT-016: OpenBao secrets integration
  - [ ] evaluate the Kubernetes secrets engine for short-lived routine deployment credentials
  - [ ] preserve the independent X.509 bootstrap/recovery path
  - [ ] define R5C-to-OpenBao machine authentication
  - [ ] verify credential TTL, renewal/reissue and revocation behavior
- [ ] PLAT-017: Restic-backed Gitea/package-state backup and restore validation
- [ ] PLAT-018: Management-plane disaster-recovery exercise

## FUTURE — Independent projects

- [ ] AWS-001: Ephemeral hybrid access via Terraform
- [ ] AWS-002: Terraform AWS networking baseline
- [ ] AWS-003: IAM and infrastructure security
- [ ] AWS-004: AWS CI/CD integration
- [ ] SEC-001: Container supply-chain controls beyond the first image scan
- [ ] OPS-001: SLO and incident response lab
- [ ] OPS-002: Automated recovery exercises
- [ ] AI-001: AI infrastructure deployment lab

- [ ] OPS-003: Reproducible interactive Zsh environment
  - Dependencies: zsh, fzf, zoxide, git-delta
  - Source: /srv/_local/scripts/bootstrap_shell.sh
  - Arguments: --human --add-root-shell
  - Keep optional; do not block platform recovery.

## Parking lot

Ideas belong here until they have a dependency, acceptance criterion, and place in the roadmap.

Cheap cleanup currently parked:

- upgrade `actions/download-artifact@v4` when convenient to remove the remaining non-blocking Node.js runtime deprecation warning;
- evaluate image signing/attestation only after digest-based retrieval and dual-registry distribution are working.
