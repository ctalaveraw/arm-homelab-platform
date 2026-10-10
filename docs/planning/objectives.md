# DevSecOps platform objective register

**93 additional, individually testable objectives across 11 workstreams.** Planned or evaluate-only as indicated. Recorded 2026-10-10; documentation does not imply implementation.

## How to read this register

- **ID:** stable future work item; retain existing PLAT-001..018, SEC-001, CI-001, OPS-001..007, AWS and AI records from the main backlog.
- **Mode:** planned unless marked *Evaluate*. Evaluation tickets may end in a documented no-adopt decision. Introduce one implementation milestone at a time.
- **Tier:** P = portable CI/off-lab; S = throwaway simulation; H = physical/site evidence. A slash means both tiers matter.
- **Dependency:** planning predecessor or existing milestone, **not** proof of completion. A proposed item is closed only with code/config, negative cases, operational verification and evidence in its stated tier. Existing historical sprint evidence is not rewritten.
- **Security scope:** controls are selected according to a threat model, not by maximizing installed products. Maintain exceptions with owner, reason, evidence, expiry, and compensating controls.

The user-approved target is **ARM-first portable**, **separate approval-gated operations authority**, **approved Ansible convergence**, **independent encrypted recovery root with OpenBao for routine use**, **risk-staged security gates**, and **RTO 4h/RPO 1h goals not currently achieved**. Forgejo, Backstage and Terraform secondary targets remain optional evaluations, not requirements for PLAT-012.

## Existing workstreams that remain authoritative

- PLAT-012 Prometheus/Grafana; PLAT-013 Gotify runtime alerting; PLAT-014 fourth-Pi Ansible bootstrap; PLAT-015 kubeadm node join; PLAT-016 OpenBao secrets; PLAT-017 Restic and restore; PLAT-018 management-plane disaster recovery.
- OPS-006 APT-Cacher-NG source ACL verification; OPS-007 shared trusted HTTPS; OPS-001 SLO incident exercises; OPS-002 recovery automation.
- SEC-001 serves as the original supply-chain umbrella and is expanded by SEC-009..014 below. Existing protections (Trivy, ShellCheck, Ruff, yamllint, actionlint, Compose guards, Flux RBAC) stay implemented; advanced controls are new work.
- Treat open objectives below as independently testable units, not as a mandate to complete all at once. Physical hardware and secrets cannot be inferred from a green hosted CI run.

## ENG — Code maintainability and interface design

| Objective | Mode | Acceptance / failure evidence | Dependency | Tier |
|---|---|---|---|---|
| **ENG-001 — Modularize repetitive CI/ops logic** | Planned | Reusable helpers emerge only for repeated behavior; current scripts retain CLI/exit contract and regression tests. | CI-007 | P |
| **ENG-002 — Selective Python extraction** | Evaluate | Structured API, JSON and state operations moved only when tests prove simpler/safer than shell. | ENG-001 | P |
| **ENG-003 — Ansible roles and host coverage** | Planned | Explicit role boundaries; converges existing host twice with second run unchanged and safe dry-run limits. | CI-002, DR-001 | P/H |
| **ENG-004 — Operator-friendly scripts** | Planned | Usage/errors, predictable exit codes, small command surfaces and worked examples reviewed by a second reader. | ENG-001 | P |
| **ENG-005 — Standardized automation result contract** | Planned | Pre/post results include action, target, revision, decision, status and redacted evidence without leaking secrets. | CI-006 | P/S |

## CI — Quality gates and CI/CD orchestration

| Objective | Mode | Acceptance / failure evidence | Dependency | Tier |
|---|---|---|---|---|
| **CI-002 — Ansible lint policy** | Planned | Pinned ansible-lint passes or has documented bounded exceptions; runs in hosted and local CI. | PLAT-014 | P |
| **CI-003 — Kubernetes/IaC semantic validation** | Planned | Render manifests and validate schema, policy and target versions; negative fixtures fail. | SEC-008 | P/S |
| **CI-004 — Modular pipeline job contracts** | Planned | Validate, build, test, scan, publish and promote have documented inputs/outputs and permissions. | PLAT-011 | P |
| **CI-005 — Change-aware pipelines and cache proof** | Planned | Paths reduce unnecessary work without bypassing required gates; cold/warm benchmark recorded. | CI-004 | P |
| **CI-006 — Preflight/postflight and rollback checks** | Planned | Each mutating operation has identity, authorization, state and artifact checks plus recorded final verification. | OPS-009 | P/H |
| **CI-007 — Offline-capable unit/integration tests** | Planned | Portable tests run on hosted ARM64; simulated and physical-only tests are visibly differentiated. | DX-001 | P/S |
| **CI-008 — Reproducible toolchains and runner images** | Planned | Pin/document dependencies and platform versions; clean runner reproduces same checks. | CI-002 | P/S |
| **CI-009 — Workflow resiliency and release event policy** | Planned | Retry, cancel, concurrency, timeout and trusted event conditions tested; no publish from untrusted contexts. | CI-004, SEC-004 | P/S |
| **CI-010 — Build cache and multi-platform test matrix** | Evaluate | BuildKit caching measured; arm64 source remains canonical, second target tested without rebuilding release identity. | CI-005, PORT-001 | P/S |
| **CI-011 — Job artifact contract and retention** | Planned | Names, digests, manifests, access and expiry declared; tampered and missing handoffs are rejected. | CI-004, SEC-010 | P |

## OPS — Out-of-cluster host operations

| Objective | Mode | Acceptance / failure evidence | Dependency | Tier |
|---|---|---|---|---|
| **OPS-008 — Dedicated trusted operations runner** | Planned | Distinct identity/execution boundary from existing validation runner; untrusted PR cannot obtain privileged access. | SEC-004, DR-001 | S/H |
| **OPS-009 — Approval-gated Ansible operations** | Planned | Allowlisted signed/reviewed scripts/playbooks; actor approval, concurrency lock, dry-run/rollback evidence and bounded privileges. | OPS-008, ENG-003 | H |
| **OPS-010 — Negative SD/systemd/Compose contracts** | Planned | Tests simulate wrong/missing filesystem, label, symlink and bind; startup refuses unsafe state. | CI-007 | P/H |
| **OPS-011 — Optional APT cache clients** | Planned | Finish OPS-006 ACL checks; test real Pi cold/warm install and bypass on cache outage. | OPS-006, PLAT-014 | H |
| **OPS-012 — Idempotent service integration seeding** | Planned | Gitea/monitor/notification config reconciliation is repeatable, non-secret in Git and restore-safe. | OPS-013, PLAT-013 | S/H |
| **OPS-013 — Environment and configuration contract** | Planned | Classify vars, .env.example, file injection and restricted config; ensure cleartext secrets never enter Git/logs. | DR-004 | P/H |
| **OPS-014 — HTTPS PKI and trust deployment** | Planned | Close OPS-007 with certificate renewal, trusted CA deployment, client validation and failure exercise. | OPS-007, DR-005 | H |
| **OPS-015 — Audited operations job lifecycle** | Planned | Approval, scheduler, retention, execution identity, timeout, replay resistance and incident log proved. | OPS-009 | H |
| **OPS-016 — Patch and OS upgrade lifecycle** | Planned | Version matrix, staging, rollback/reboot safety, maintenance windows and host recovery checks. | ENG-003, DR-003 | H |
| **OPS-017 — Cross-service dependency health** | Planned | Monitor Gitea, OCI, runner, Gotify, Kuma, APT, DNS and storage; broken dependency detected accurately. | PLAT-012, PLAT-013 | H |
| **OPS-018 — Capacity and wear management** | Planned | ARM CPU/memory, SD health/writes, cache limits and storage growth alert thresholds measured. | PLAT-012 | H |
| **OPS-019 — Service boot-order failure drills** | Planned | Network/DNS/SD/Docker outage at boot proves systemd startup ownership; documented recovery path. | OPS-010, DR-003 | H |

## OBS — Observability and operational reliability

| Objective | Mode | Acceptance / failure evidence | Dependency | Tier |
|---|---|---|---|---|
| **OBS-001 — Infrastructure metrics coverage** | Planned | PLAT-012 collects Pi, K8s, Flux and R5C measurements with cardinality and retention budget. | PLAT-012 | H |
| **OBS-002 — Actionable alert delivery** | Planned | PLAT-013 maps observed failures to deduplicated Gotify notifications with recovery/silence checks. | PLAT-013 | H |
| **OBS-003 — Structured logs and event correlation** | Planned | Trace action, image digest, Flux revision and incident in accessible redacted logs. | PLAT-012, SEC-019 | H |
| **OBS-004 — SLO/SLI and error-budget lab** | Planned | Choose critical user-visible journey, target and burn alert; run controlled violation and response. | OPS-001, PLAT-013 | H |
| **OBS-005 — Incident runbooks and game days** | Planned | Repeatable detection/triage/mitigation/restore evidence, incident ownership and postmortem. | OBS-002, DR-010 | H |
| **OBS-006 — Traceability/optional tracing evaluation** | Evaluate | Determine whether app tracing adds value, benchmark resource cost, adopt only with concrete span/use case. | OBS-003 | S/H |

## REL — Release, promotion and lifecycle management

| Objective | Mode | Acceptance / failure evidence | Dependency | Tier |
|---|---|---|---|---|
| **REL-001 — Digest-driven GitOps promotion** | Planned | Approved digest PR enters protected main only after qualified attestations; Flux remains sole application state owner. | SEC-012 | P/H |
| **REL-002 — Release manifest and changelog contract** | Planned | Commit/build provenance, image digest, policy result and deployment revision recorded per release. | SEC-010 | P |
| **REL-003 — Environment promotion and drift isolation** | Planned | A second isolated environment exercises promotion/rollback without split-brain writers. | PORT-002, REL-001 | S/H |
| **REL-004 — Registry retention and disaster recovery** | Planned | Retention/GC does not delete running digests; replication/restore testing respects immutable references. | PLAT-017, DR-006 | H |
| **REL-005 — Controlled rollback and progressive delivery** | Planned | Rollout health, negative change and recovery tested; assess canary only when traffic shape supports it. | OBS-002, REL-001 | H |
| **REL-006 — Release policy and exception enforcement** | Planned | Approved/rejected provenance, vulnerability, expiry and rollback outcomes tested end-to-end. | SEC-013, SEC-021 | S/H |

## SEC — DevSecOps security and assurance (SEC-001 is existing supply-chain umbrella)

| Objective | Mode | Acceptance / failure evidence | Dependency | Tier |
|---|---|---|---|---|
| **SEC-002 — Threat modeling and asset register** | Planned | Data-flow/STRIDE-style risks, trust actors, recovery roots and abuse cases documented with owners. | ADR-0010..0013 | P |
| **SEC-003 — SCM and code review governance** | Planned | Protected main, CODEOWNERS/review critical paths, workflow change scrutiny and test bypass denied. | SEC-002 | P |
| **SEC-004 — CI runner boundary and injection defense** | Planned | Fork/untrusted workflow cannot reach internal authority or leak tokens; approval and isolation negative tests. | OPS-008 | P/S |
| **SEC-005 — Workflow supply-chain policy** | Planned | Pin/audit external actions, minimal permissions, evaluate workflow OIDC and verify third-party action update paths. | CI-009 | P |
| **SEC-006 — Secrets leak prevention and response** | Planned | Scan source, artifacts and logs; injected canary leak rejected; rotation/runbook exercised. | OPS-013 | P/S |
| **SEC-007 — Application SAST/SCA** | Planned | Supported-language SAST and dependency/SCA findings triaged; false-positive policy recorded. | CI-003 | P |
| **SEC-008 — IaC and infrastructure policy scanning** | Planned | Ansible, Compose, K8s and future Terraform have negative misconfiguration tests and justified suppressions. | CI-003 | P/S |
| **SEC-009 — Build-specific SBOM** | Planned | CycloneDX/SPDX manifest for exact image archived/retrievable; dependencies match built artifact. | SEC-001 | P |
| **SEC-010 — Verifiable build provenance** | Planned | Builder, workflow, source ref, materials and output digest attest independently; tampered proof rejected. | SEC-009 | P/S |
| **SEC-011 — Artifact signing and verification** | Planned | Signature bound to OCI digest/approved identity verified independently; altered/untrusted signature fails. | SEC-010 | P/S |
| **SEC-012 — Supply-chain promotion policy** | Planned | Promotion checks digest, verified signatures, provenance, test and vulnerability decision before Git desired state update. | SEC-011, REL-001 | P/S |
| **SEC-013 — Ongoing vulnerability management** | Planned | Scheduled rescans, advisory intake, severity+exploitability/aging gates and reissue of approved releases. | SEC-007 | P |
| **SEC-014 — Dependency/image/action update strategy** | Planned | Controlled updates and rollback with tests; no unreviewed automatic privileged upgrades. | SEC-013 | P |
| **SEC-015 — Kubernetes admission policy** | Planned | Explicit policy phase-in, exempt recovery namespaces only by documented design; reject noncompliant test Pods. | SEC-012, PLAT-014 | S/H |
| **SEC-016 — Pod and container runtime hardening** | Planned | Non-root, readonly fs, seccomp, cap drop, bounded resources and ServiceAccounts test positive/negative. | SEC-015 | S/H |
| **SEC-017 — Network segmentation and egress policy** | Planned | Default-deny where supported; allowed DNS/registry/monitor paths work, forbidden paths fail. | SEC-015, PORT-001 | H |
| **SEC-018 — ARM runtime detection evaluation** | Evaluate | Measure Falco/Tetragon/alternative feasibility, CPU budget and signal fidelity; only adopt justified option. | PLAT-012, SEC-016 | H |
| **SEC-019 — Audit log capture and retention** | Planned | Git, Gitea, runner, Ansible, API and K8s security events centrally correlated and access-controlled. | OBS-003 | H |
| **SEC-020 — Incident containment and response** | Planned | Simulate compromised CI identity/registry/K8s token; detect, revoke, recover and document outcomes. | SEC-019, DR-005 | H |
| **SEC-021 — Security policy as code and exceptions** | Planned | Reviewable ownership/severity decisions; expires bounded exception; unwarranted waiver fails CI. | SEC-002, SEC-013 | P/S |
| **SEC-022 — DAST and API authorization checks** | Planned | Scoped sandbox HTTP/API tests including denied identity paths; no unsafe broad production scans. | CI-007 | S/H |
| **SEC-023 — Compliance/evidence mapping** | Planned | NIST SSDF/OWASP/CIS controls mapped to repo tests or explicit gaps; no unsupported compliance claim. | SEC-002 | P |
| **SEC-024 — Periodic security scorecard** | Planned | Actionable delta report tracks control findings, open exceptions and measured remediation without vanity scoring. | SEC-023 | P |
| **SEC-025 — Identity inventory and privilege review** | Planned | Human/machine/runner/Flux/Git/registry identities, scopes, expiry and access revocation demonstrated. | DR-005 | P/H |
| **SEC-026 — Data integrity, encryption and access** | Planned | Backups, config, transport and storage integrity classified; encryption/key handling and unauthorized reads tested. | DR-004, DR-009 | S/H |
| **SEC-027 — Secure base images and patch windows** | Planned | Minimal base selection, immutable pin, rebuild cadence, update risk and provenance tests established. | SEC-013 | P/S |
| **SEC-028 — Policy enforcement negative-test suite** | Planned | Known bad manifests, credentials, signature and workflow examples rejected in portable/simulated CI. | SEC-015, SEC-021 | P/S |
| **SEC-029 — GitOps controller and bootstrap audit** | Planned | Impersonation, cluster-admin bootstrap, cross-namespace references and self-management denial retested on updates. | PLAT-011 | H |
| **SEC-030 — Host hardening and service permissions** | Planned | SSH, sudo, firewall, systemd sandbox, file rights and patch policy measured; deny unsafe changes. | OPS-016, DR-003 | H |
| **SEC-031 — Backup/restore adversarial security drill** | Planned | Compromised/altered backup, unavailable key and missing trust root fail securely; safe restore proven. | DR-009 | H |

## DR — Day-zero bootstrap, state recovery and disaster recovery

| Objective | Mode | Acceptance / failure evidence | Dependency | Tier |
|---|---|---|---|---|
| **DR-001 — Blank-device bootstrap** | Planned | From documented off-device media/source provision OS, operator, SSH/trust, Python/Ansible and supported architecture. | PLAT-018 | H |
| **DR-002 — Network and storage reconstruction** | Planned | Restore interfaces/DNS, SD partition/UUID/label, mount/automount and safety contract from blank host. | DR-001 | H |
| **DR-003 — Host/service convergence** | Planned | Freshly rebuilt machine safely installs Docker/systemd units and recreates service lifecycles from Git. | DR-002, ENG-003 | H |
| **DR-004 — Mutable state and configuration restoration** | Planned | Restore consistent Gitea/OCI/monitor service configs with independent encrypted material; no unknown manual steps. | PLAT-017, OPS-013 | H |
| **DR-005 — PKI and certificate recovery** | Planned | Reissue/rotate/revoke break-glass X.509/CA trust and tokens after expiration/compromise, preserving scoped access. | DR-001 | H |
| **DR-006 — Gitea, registry and runner reconstruction** | Planned | Restore repositories/packages/mirror/jobs identity; runner can be safely re-registered, without forge dependency. | PLAT-017, DR-004 | H |
| **DR-007 — Kubernetes bootstrap trust recovery** | Planned | Rebuild namespace/RBAC/Flux CRDs/controllers/sources and scoped credentials without relying on a live R5C. | DR-005, PLAT-015 | H |
| **DR-008 — etcd and cluster control-plane recovery** | Planned | Consistent snapshot capture/restore and fresh cluster versus same-cluster migration delineated and tested. | DR-007 | H |
| **DR-009 — Off-device backup design and verification** | Planned | Encrypted/versioned independent backups, integrity and consistency tests, measured 1h RPO target within classified scope. | PLAT-017, DR-004 | H |
| **DR-010 — Timed isolated disaster-recovery drill** | Planned | Loss of R5C/Gitea/SD (and separate cluster scenario) measured toward 4h RTO and 1h RPO; report gaps. | PLAT-018, DR-009 | H |
| **DR-011 — Recovery key escrow and rotation** | Planned | At least two documented independent authorized paths to decryption; revoke/rekey, compromised and lost key exercises. | DR-004, DR-005 | H |
| **DR-012 — Failure dependency matrix** | Planned | DNS, network, power, clock, external Git, TLS CA, storage, OpenBao and registry outage order documented/tested. | DR-001, SEC-002 | P/H |

## PORT — Portability and infrastructure adapters

| Objective | Mode | Acceptance / failure evidence | Dependency | Tier |
|---|---|---|---|---|
| **PORT-001 — Environment contracts and capability matrix** | Planned | ARM primary and second target declare inventory, OS/arch, DNS, storage, K8s, secret and test requirements. | ENG-003 | P |
| **PORT-002 — Proxmox Terraform reference lab** | Evaluate | Terraform provisions isolated test VMs/network; Ansible configures OS; Flux app authority unchanged. | PORT-001, DR-001 | S |
| **PORT-003 — Forgejo isolated migration evaluation** | Evaluate | Backup/export/import feasibility, DB/OCI/actions/identity compatibility and tested rollback; no in-place assumption. | DR-006 | S |
| **PORT-004 — IaC state and provider trust** | Planned | Remote/local state protection, locking, secret handling, drift and destruction guardrails tested. | PORT-002 | S |
| **PORT-005 — Scale-out and multi-site test** | Evaluate | Multiple worker/site targets without cross-environment secret, runner or GitOps ownership bleed. | PORT-001, REL-003 | S/H |

## DX — Off-lab development and developer workflow

| Objective | Mode | Acceptance / failure evidence | Dependency | Tier |
|---|---|---|---|---|
| **DX-001 — Tiered off-lab contribution path** | Planned | Public PR runs portable checks independently of R5C, labels S/H pending gates and cannot leak internal data. | CI-007 | P |
| **DX-002 — Reproducible contributor environment** | Planned | Document local tool bootstrap, test commands, CPU/arch requirements and offline fixtures from clean checkout. | DX-001 | P |
| **DX-003 — Trusted testing/evidence handoff** | Planned | Offline code reviewers can merge eligible changes; H-gated work queues named lab operator test and proof. | DX-001, CI-006 | P/H |

## IDP — Internal developer platform evaluation

| Objective | Mode | Acceptance / failure evidence | Dependency | Tier |
|---|---|---|---|---|
| **IDP-001 — Backstage/developer portal assessment** | Evaluate | Compare catalog, tech docs and templates with lightweight alternatives; decision justified by app/team needs. | PORT-005 | P |
| **IDP-002 — Self-service golden-path proof** | Evaluate | If justified, template creates repo, CI, policy, provenance and Flux app path with no privileged portal bootstrap. | IDP-001, SEC-012 | S |

## DOC — Human documentation and portfolio capstone

| Objective | Mode | Acceptance / failure evidence | Dependency | Tier |
|---|---|---|---|---|
| **DOC-001 — Human-centered documentation capstone** | Planned | Cold reader navigates architecture, operations, security, failure modes and evidence without chat history; prose rewritten by owner. | DR-010, SEC-023 | P/H |
| **DOC-002 — Repository information architecture** | Planned | Explicit quickstart, operator/security/contributor guides, status matrix, glossary, diagrams and historical-vs-current separation. | DOC-001 | P |

## Execution sequencing and non-goals

- **Immediate adjuncts:** CI-002 before PLAT-014; CI-003/SEC-008 as manifest complexity grows; OPS-010 when altering the storage guard; DX-001 in all future hosted checks.
- **Observability first:** PLAT-012 and PLAT-013 before runtime detection, SLOs, operations automation and the next recovery fire drills.
- **Reconstruction:** PLAT-014/015 plus DR-001/002/003 establish day-zero host and worker capabilities; these must not be confused with actual backup restore.
- **Secrets and recovery:** OPS-007 before trusting management APIs; PLAT-016 plus DR-004/005/011, PLAT-017/018 plus DR-006..010. High-confidence restore is required before citing RTO/RPO achievements.
- **Post-core-maturity:** privileged ops runner, Forgejo migration rehearsal, Terraform second target and Backstage assessment, unless a specific dependency drives an earlier isolated prototype.
- **Do not do:** convert all scripts to Python, give existing Gitea validation runner privileged credentials, let CI and Flux both apply the same app desired state, require Gitea/OpenBao to resurrect themselves, expose host Docker socket to generic PR jobs, interpret a passing scan as provenance, or treat proposed targets as service guarantees.

## Acceptance/evidence template for implementing a ticket

Document: threat/problem; current behavior; desired owner; dependency and rollback; positive test; negative test; tier P/S/H; exact artifact/runtime/revision; permissions and secret handling; operator runbook; status and known limitations. Close only after applicable checks and PR review. Update the backlog state, current architecture, and engineering evidence if this capability has been proven.
