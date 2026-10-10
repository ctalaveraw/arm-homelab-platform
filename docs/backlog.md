# Platform Engineering Backlog

## Working agreement

- One active delivery milestone at a time.
- New ideas enter the backlog instead of interrupting the current gate.
- A milestone is not complete until implementation **and** verification are recorded.
- Architecture decisions belong in `docs/adr/`.
- Interview-relevant proof belongs in `docs/interview/`.
- Historical sprint/incident records remain historical.
- Delivery gates include a short knowledge check so implementation can be defended conversationally.

## COMPLETE — Core delivery

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

- [x] PLAT-010: Deployment failure and rollback exercise

## NOW — Platform maturity

- [x] PLAT-011: Flux GitOps reconciliation
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

## Tracked future DevSecOps and platform objective register

The [platform charter](vision/platform-charter.md) and [93-objective register](planning/objectives.md) convert the planning ideas into stable work IDs with acceptance, dependencies and P/S/H evidence tiers. Work is queued, **not implemented**. Approved architecture choices and unresolved implementation gates are in [design gates](planning/design-gates.md). Existing PLAT-012..018 retain priority; only one milestone is active at a time. Evaluation items may legitimately close with a reasoned no-adopt decision.

### ENG — Code maintainability and interface design

- [ ] ENG-001: Modularize repetitive CI/ops logic ([acceptance](planning/objectives.md#eng--code-maintainability-and-interface-design))
- [ ] ENG-002: Selective Python extraction ([acceptance](planning/objectives.md#eng--code-maintainability-and-interface-design))
- [ ] ENG-003: Ansible roles and host coverage ([acceptance](planning/objectives.md#eng--code-maintainability-and-interface-design))
- [ ] ENG-004: Operator-friendly scripts ([acceptance](planning/objectives.md#eng--code-maintainability-and-interface-design))
- [ ] ENG-005: Standardized automation result contract ([acceptance](planning/objectives.md#eng--code-maintainability-and-interface-design))

### CI — Quality gates and CI/CD orchestration

- [ ] CI-002: Ansible lint policy ([acceptance](planning/objectives.md#ci--quality-gates-and-cicd-orchestration))
- [ ] CI-003: Kubernetes/IaC semantic validation ([acceptance](planning/objectives.md#ci--quality-gates-and-cicd-orchestration))
- [ ] CI-004: Modular pipeline job contracts ([acceptance](planning/objectives.md#ci--quality-gates-and-cicd-orchestration))
- [ ] CI-005: Change-aware pipelines and cache proof ([acceptance](planning/objectives.md#ci--quality-gates-and-cicd-orchestration))
- [ ] CI-006: Preflight/postflight and rollback checks ([acceptance](planning/objectives.md#ci--quality-gates-and-cicd-orchestration))
- [ ] CI-007: Offline-capable unit/integration tests ([acceptance](planning/objectives.md#ci--quality-gates-and-cicd-orchestration))
- [ ] CI-008: Reproducible toolchains and runner images ([acceptance](planning/objectives.md#ci--quality-gates-and-cicd-orchestration))
- [ ] CI-009: Workflow resiliency and release event policy ([acceptance](planning/objectives.md#ci--quality-gates-and-cicd-orchestration))
- [ ] CI-010: Build cache and multi-platform test matrix ([acceptance](planning/objectives.md#ci--quality-gates-and-cicd-orchestration))
- [ ] CI-011: Job artifact contract and retention ([acceptance](planning/objectives.md#ci--quality-gates-and-cicd-orchestration))

### OPS — Out-of-cluster host operations

- [ ] OPS-008: Dedicated trusted operations runner ([acceptance](planning/objectives.md#ops--out-of-cluster-host-operations))
- [ ] OPS-009: Approval-gated Ansible operations ([acceptance](planning/objectives.md#ops--out-of-cluster-host-operations))
- [ ] OPS-010: Negative SD/systemd/Compose contracts ([acceptance](planning/objectives.md#ops--out-of-cluster-host-operations))
- [ ] OPS-011: Optional APT cache clients ([acceptance](planning/objectives.md#ops--out-of-cluster-host-operations))
- [ ] OPS-012: Idempotent service integration seeding ([acceptance](planning/objectives.md#ops--out-of-cluster-host-operations))
- [ ] OPS-013: Environment and configuration contract ([acceptance](planning/objectives.md#ops--out-of-cluster-host-operations))
- [ ] OPS-014: HTTPS PKI and trust deployment ([acceptance](planning/objectives.md#ops--out-of-cluster-host-operations))
- [ ] OPS-015: Audited operations job lifecycle ([acceptance](planning/objectives.md#ops--out-of-cluster-host-operations))
- [ ] OPS-016: Patch and OS upgrade lifecycle ([acceptance](planning/objectives.md#ops--out-of-cluster-host-operations))
- [ ] OPS-017: Cross-service dependency health ([acceptance](planning/objectives.md#ops--out-of-cluster-host-operations))
- [ ] OPS-018: Capacity and wear management ([acceptance](planning/objectives.md#ops--out-of-cluster-host-operations))
- [ ] OPS-019: Service boot-order failure drills ([acceptance](planning/objectives.md#ops--out-of-cluster-host-operations))

### OBS — Observability and operational reliability

- [ ] OBS-001: Infrastructure metrics coverage ([acceptance](planning/objectives.md#obs--observability-and-operational-reliability))
- [ ] OBS-002: Actionable alert delivery ([acceptance](planning/objectives.md#obs--observability-and-operational-reliability))
- [ ] OBS-003: Structured logs and event correlation ([acceptance](planning/objectives.md#obs--observability-and-operational-reliability))
- [ ] OBS-004: SLO/SLI and error-budget lab ([acceptance](planning/objectives.md#obs--observability-and-operational-reliability))
- [ ] OBS-005: Incident runbooks and game days ([acceptance](planning/objectives.md#obs--observability-and-operational-reliability))
- [ ] OBS-006: Traceability/optional tracing evaluation ([acceptance](planning/objectives.md#obs--observability-and-operational-reliability))

### REL — Release, promotion and lifecycle management

- [ ] REL-001: Digest-driven GitOps promotion ([acceptance](planning/objectives.md#rel--release-promotion-and-lifecycle-management))
- [ ] REL-002: Release manifest and changelog contract ([acceptance](planning/objectives.md#rel--release-promotion-and-lifecycle-management))
- [ ] REL-003: Environment promotion and drift isolation ([acceptance](planning/objectives.md#rel--release-promotion-and-lifecycle-management))
- [ ] REL-004: Registry retention and disaster recovery ([acceptance](planning/objectives.md#rel--release-promotion-and-lifecycle-management))
- [ ] REL-005: Controlled rollback and progressive delivery ([acceptance](planning/objectives.md#rel--release-promotion-and-lifecycle-management))
- [ ] REL-006: Release policy and exception enforcement ([acceptance](planning/objectives.md#rel--release-promotion-and-lifecycle-management))

### SEC — DevSecOps security and assurance (SEC-001 is existing supply-chain umbrella)

- [ ] SEC-002: Threat modeling and asset register ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-003: SCM and code review governance ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-004: CI runner boundary and injection defense ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-005: Workflow supply-chain policy ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-006: Secrets leak prevention and response ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-007: Application SAST/SCA ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-008: IaC and infrastructure policy scanning ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-009: Build-specific SBOM ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-010: Verifiable build provenance ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-011: Artifact signing and verification ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-012: Supply-chain promotion policy ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-013: Ongoing vulnerability management ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-014: Dependency/image/action update strategy ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-015: Kubernetes admission policy ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-016: Pod and container runtime hardening ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-017: Network segmentation and egress policy ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-018: ARM runtime detection evaluation ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-019: Audit log capture and retention ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-020: Incident containment and response ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-021: Security policy as code and exceptions ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-022: DAST and API authorization checks ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-023: Compliance/evidence mapping ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-024: Periodic security scorecard ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-025: Identity inventory and privilege review ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-026: Data integrity, encryption and access ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-027: Secure base images and patch windows ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-028: Policy enforcement negative-test suite ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-029: GitOps controller and bootstrap audit ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-030: Host hardening and service permissions ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))
- [ ] SEC-031: Backup/restore adversarial security drill ([acceptance](planning/objectives.md#sec--devsecops-security-and-assurance-sec-001-is-existing-supply-chain-umbrella))

### DR — Day-zero bootstrap, state recovery and disaster recovery

- [ ] DR-001: Blank-device bootstrap ([acceptance](planning/objectives.md#dr--day-zero-bootstrap-state-recovery-and-disaster-recovery))
- [ ] DR-002: Network and storage reconstruction ([acceptance](planning/objectives.md#dr--day-zero-bootstrap-state-recovery-and-disaster-recovery))
- [ ] DR-003: Host/service convergence ([acceptance](planning/objectives.md#dr--day-zero-bootstrap-state-recovery-and-disaster-recovery))
- [ ] DR-004: Mutable state and configuration restoration ([acceptance](planning/objectives.md#dr--day-zero-bootstrap-state-recovery-and-disaster-recovery))
- [ ] DR-005: PKI and certificate recovery ([acceptance](planning/objectives.md#dr--day-zero-bootstrap-state-recovery-and-disaster-recovery))
- [ ] DR-006: Gitea, registry and runner reconstruction ([acceptance](planning/objectives.md#dr--day-zero-bootstrap-state-recovery-and-disaster-recovery))
- [ ] DR-007: Kubernetes bootstrap trust recovery ([acceptance](planning/objectives.md#dr--day-zero-bootstrap-state-recovery-and-disaster-recovery))
- [ ] DR-008: etcd and cluster control-plane recovery ([acceptance](planning/objectives.md#dr--day-zero-bootstrap-state-recovery-and-disaster-recovery))
- [ ] DR-009: Off-device backup design and verification ([acceptance](planning/objectives.md#dr--day-zero-bootstrap-state-recovery-and-disaster-recovery))
- [ ] DR-010: Timed isolated disaster-recovery drill ([acceptance](planning/objectives.md#dr--day-zero-bootstrap-state-recovery-and-disaster-recovery))
- [ ] DR-011: Recovery key escrow and rotation ([acceptance](planning/objectives.md#dr--day-zero-bootstrap-state-recovery-and-disaster-recovery))
- [ ] DR-012: Failure dependency matrix ([acceptance](planning/objectives.md#dr--day-zero-bootstrap-state-recovery-and-disaster-recovery))

### PORT — Portability and infrastructure adapters

- [ ] PORT-001: Environment contracts and capability matrix ([acceptance](planning/objectives.md#port--portability-and-infrastructure-adapters))
- [ ] PORT-002: Proxmox Terraform reference lab ([acceptance](planning/objectives.md#port--portability-and-infrastructure-adapters))
- [ ] PORT-003: Forgejo isolated migration evaluation ([acceptance](planning/objectives.md#port--portability-and-infrastructure-adapters))
- [ ] PORT-004: IaC state and provider trust ([acceptance](planning/objectives.md#port--portability-and-infrastructure-adapters))
- [ ] PORT-005: Scale-out and multi-site test ([acceptance](planning/objectives.md#port--portability-and-infrastructure-adapters))

### DX — Off-lab development and developer workflow

- [ ] DX-001: Tiered off-lab contribution path ([acceptance](planning/objectives.md#dx--off-lab-development-and-developer-workflow))
- [ ] DX-002: Reproducible contributor environment ([acceptance](planning/objectives.md#dx--off-lab-development-and-developer-workflow))
- [ ] DX-003: Trusted testing/evidence handoff ([acceptance](planning/objectives.md#dx--off-lab-development-and-developer-workflow))

### IDP — Internal developer platform evaluation

- [ ] IDP-001: Backstage/developer portal assessment ([acceptance](planning/objectives.md#idp--internal-developer-platform-evaluation))
- [ ] IDP-002: Self-service golden-path proof ([acceptance](planning/objectives.md#idp--internal-developer-platform-evaluation))

### DOC — Human documentation and portfolio capstone

- [ ] DOC-001: Human-centered documentation capstone ([acceptance](planning/objectives.md#doc--human-documentation-and-portfolio-capstone))
- [ ] DOC-002: Repository information architecture ([acceptance](planning/objectives.md#doc--human-documentation-and-portfolio-capstone))

## Parking lot

Ideas belong here until they have a dependency, acceptance criterion, and place in the roadmap.

Remaining unscoped ideas enter here only after deduplication against the objective register. Artifact signing, provenance and attestations now have explicit SEC-009..012 objectives; future tooling choices remain evaluation decisions.
