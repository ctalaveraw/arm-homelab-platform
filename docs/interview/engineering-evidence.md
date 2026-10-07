# Engineering Evidence Ledger

Purpose: Record verifiable engineering work and
preserve the reasoning behind implementation.

## EVIDENCE-001: Management Storage Baseline

Date: 2026-10-01

Problem:
The management host initially lacked documented
storage and service namespace conventions.

Implementation:
- Established /srv/platform.
- Established /srv/services.
- Established /srv/storage/state.
- Established /srv/storage/archive.
- Recorded ADR-0001.

Verification:
- findmnt --verify passed.
- Active mounts inspected.
- Filesystem capacity verified.

Evidence:
- Commit 3e8e218.
- docs/adr/0001-storage-layout.md.
- docs/architecture/r5c-baseline.md.

## EVIDENCE-002: SD Storage Migration

Date: 2026-10-02

Change:
Replaced the original 32 GB SD card with a
128 GB SD card.

Preserved:
- Filesystem label: storage_sdcard
- Mount point: /srv/storage/state
- Filesystem type: ext4

Observed:
- New device size: 119.2 GiB.
- Filesystem size: approximately 117 GiB.
- Available capacity: approximately 109 GiB.
- Active filesystem mounted rw,noatime.
- fstab uses LABEL=storage_sdcard.
- findmnt --verify passed.

Outstanding at time of measurement:
- [ ] Validate persistence after reboot.
- [ ] Enforce service mount dependencies.

Update (2026-10-04): per-service SD storage guards were
implemented and tested. Full-host reboot verification
remains a separate outstanding test.

Learning objective:
Explain LABEL versus UUID versus mount point,
and the operational effects of nofail/automount.


## EVIDENCE-003: Ansible Management Baseline

Date: 2026-10-03

Implementation:
- Created local R5C inventory.
- Added architecture and SD storage assertions.
- Established reusable common role.
- Declaratively managed package and directory state.

Verification:
- Preflight passed.
- Required SD filesystem validated.
- Directory execution initially changed one resource.
- Subsequent execution reported changed=0.

Evidence:
- Commit 03d217c.
- Commit 48465e0.

Limitations:
- Full fresh-host reconstruction remains untested.

## EVIDENCE-004: Docker Runtime Bootstrap

Date: 2026-10-03

Implementation:
- Created docker_host role.
- Installed docker.io, docker-cli and docker-compose.
- Declaratively enabled and started docker.service.
- Retained Docker data root on eMMC.

Verification:
- First corrected package execution changed=1.
- Subsequent execution changed=0.
- Docker client/server verified: 26.1.5.
- Standalone Compose verified: 2.26.1.
- Docker and containerd active.
- Docker enabled at boot.
- Data root: /var/lib/docker.

Engineering lesson:
Idempotent configuration does not guarantee that
the declared dependency list is complete. Runtime
verification exposed the initially missing Docker CLI.

Evidence:
- Commit 989c5d8.

## EVIDENCE-005: Gotify Notification Service

Date: 2026-10-04

Problem:
The management platform lacked an operational
notification destination for future CI/CD and incidents.

Implementation:
- Deployed Gotify 3.1.1 on ARM64.
- Reused Ansible, Compose and guarded systemd lifecycle.
- Persisted application state on validated SD storage.
- Integrated a DNS-based service identity.

Verification:
- Positive and negative storage tests passed.
- First authenticated API notification returned HTTP 200.
- Browser receipt independently confirmed.
- Application and message survived container recreation.
- Service active and enabled after recreation.

Trade-offs:
- LAN HTTP is temporary.
- Gotify is now monitored through Uptime Kuma, although both
  services share the same management-host failure domain.
- Off-device application restore remains untested.

## EVIDENCE-006: Service Monitoring and Recovery

Date: 2026-10-04

Implementation:
- Deployed persistent Uptime Kuma on ARM64.
- Established Gitea and Gotify HTTP monitoring.
- Integrated Gotify incident notifications.

Verification:
- Positive and negative storage tests passed.
- Ansible converged with changed=0.
- Controlled Gitea outage generated a real DOWN alert.
- Guarded recovery generated a subsequent UP alert.
- Monitoring targets survived Kuma container recreation.

Trade-offs:
- Monitoring shares a failure domain with notification delivery.
- Off-device recovery and full-host outage detection are pending.

Evidence:
- docs/sprints/04-uptime-kuma.md
- docs/incidents/2026-10-04-gitea-controlled-outage.md

## EVIDENCE-007: Shared APT Package Cache

Date: 2026-10-04

Implementation:
- Deployed ARM64 APT-Cacher-NG.
- Reused Ansible, Compose and guarded systemd lifecycle.
- Persisted cache data on SD-backed ext4.
- Declaratively enabled and started the service.
- Added HTTP monitoring through Uptime Kuma.

Verification:
- Ansible converged with changed=0.
- Storage guard rejected an incorrect binding.
- First package request: 199.713 ms.
- Identical subsequent request: 15.229 ms.
- SHA-256 checksums matched.
- Server logs demonstrated package-cache reuse.
- Cache survived container recreation.
- Post-restart retrieval completed in 15.813 ms.

Limitations:
- Single-package comparison; not a full CI benchmark.
- Network source ACL verification remains pending.
- A hard capacity quota has not been established.
- Full-host reboot and expiry execution remain untested.

Evidence:
- docs/benchmarks/2026-10-04-apt-cacher-ng.md
- docs/sprints/05-apt-cacher-ng.md

## EVIDENCE-008: Portable ARM64 Repository CI

Date: 2026-10-04

Implementation:
- Kept GitHub Actions YAML thin: checkout, dependency bootstrap and one
  repository-owned validation entrypoint.
- Added scripts/ci/bootstrap.sh and scripts/ci/validate.sh.
- Added three Python unittest checks enforcing Compose storage, restart
  policy, and explicit binding contracts.
- Validation runs on GitHub's ARM64 hosted runner and locally.

Verification:
- Three successive GitHub Actions runs completed successfully.
- Run #3 reported aarch64, passed the three contract tests and completed
  full repository validation.
- The hosted run also performed ShellCheck.

Evidence:
- Commit a5d3222: portable validation entrypoints.
- Commit 3e58f61: Compose safety-contract tests.
- https://github.com/ctalaveraw/arm-homelab-platform/actions/runs/37186219090
- docs/sprints/06-ci-foundation.md

Limits:
- Static validation, not application integration or deployment testing.
- It does not reproduce the physical SD mount on a hosted runner.

## EVIDENCE-009: Canonical GitHub and Private Gitea Pull Mirror

Date: 2026-10-04

Implementation:
- Retained GitHub as off-device canonical and recovery repository.
- Created the Gitea repository using its native pull-mirror import.

Verification:
- Gitea showed the repository as a GitHub mirror with recent sync.
- Gitea's displayed main HEAD and GitHub ls-remote both matched
  3e58f61e8855b41623490c560f90f774b72ca3f0.

Limits:
- The original observation did not establish a recurring synchronization SLA.
- GitHub Actions history/secrets are not replicated by a Git mirror.

Update (2026-10-04):
- A repository-scoped Gitea Actions runner is now operational on the R5C.
- Forced mirror synchronization generated a push event that triggered native validation.
- GitHub remains canonical; the mirror remains one-way.

## EVIDENCE-010: Native Gitea Actions on Physical ARM64

Date: 2026-10-04

Implementation:
- Built a purpose-specific ARM64 Gitea runner image.
- Registered runner at repository scope.
- Persisted runner identity on guarded SD storage.
- Ran the runner as UID/GID 10001 without privileged mode or a host Docker socket.
- Reused the same repository-owned bootstrap and validation entrypoints as GitHub Actions.
- Added Ansible ownership for runner storage, systemd unit installation, enablement and startup.

Verification:
- Runner storage playbook converged with changed=0.
- Runner declared successfully to Gitea.
- Gitea Actions run #1 completed successfully on the physical NanoPi R5C.
- Run details showed a push trigger on main after mirror synchronization.
- Four Compose safety-contract tests passed.

Trade-offs:
- Host-mode jobs share the trusted runner container environment.
- The runner is for trusted repository validation, not arbitrary untrusted PR execution.
- No deployment, registry or Kubernetes credentials are present.

Evidence:
- docs/sprints/07-native-gitea-ci.md
- docs/evidence/plat-006/

What I learned:
A self-hosted runner is an execution boundary, not merely another service. Registration scope, persisted identity, runtime privilege, and access to the host Docker daemon materially change the risk profile.

## EVIDENCE-011: First ARM64 Application Build and Runtime Acceptance

Date: 2026-10-04

Problem:
Repository validation existed, but the platform had not yet proven that CI could build and exercise an application image.

Implementation:
- Added apps/platform-hello with a minimal static HTML workload.
- Built the image for Linux ARM64.
- Ran the application as UID/GID 10001.
- Added scripts/ci/test-hello.sh for architecture, runtime identity, readiness and content checks.
- Added a dependent GitHub Actions build-hello job using needs: validate.
- Added Docker Buildx --check before the build job.
- Upgraded GitHub checkout actions to v5, removing the observed Node.js 20 warning.

Verification:
- Local ARM64 image and HTTP acceptance passed.
- Readiness polling demonstrated that container-running state can precede HTTP readiness.
- GitHub-hosted ARM64 validate and build-hello jobs both passed.
- The application build remains gated on repository validation.

Trade-offs at the time of this evidence:
- The test script still built the image internally.
- The image was ephemeral on the hosted runner and was not yet published.
- Scan, registry publication, immutable digest capture and Kubernetes delivery were pending.

Update (2026-10-05):
- Build and test responsibilities were separated so one explicit image reference can move through later stages.
- Trivy scanning, cross-job integrity verification, and GHCR publication are now implemented.
- Kubernetes delivery remains pending.

What I learned:
CI success must be tied to the artifact produced by the current source. A stale local image or an independent rebuild after testing can break artifact identity and create misleading evidence.

## EVIDENCE-012: Repository Quality Gates and Source Convergence

Date: 2026-10-05

Problem:
The repository had grown beyond simple syntax checks, while the controller working copy, canonical GitHub repository, and private Gitea mirror did not yet have a single operator-visible convergence check.

Implementation:
- Changed CI bootstrap so an existing `.ci-venv` is converged on every run instead of assuming its dependency set is current.
- Added Ruff for tracked Python.
- Added yamllint with repository-owned policy.
- Added actionlint for GitHub Actions semantics.
- Expanded ShellCheck discovery so tracked operational scripts are covered.
- Corrected four Python storage-guard executable modes.
- Made intentional `subprocess.run(..., check=False)` behavior explicit.
- Added `scripts/ops/check-source-parity.sh`.
- Configured the controller's Gitea remote as fetch-only while retaining GitHub as the push destination.
- Protected GitHub `main` so CI-backed PR flow is enforced by repository policy.

Verification:
- Bootstrap repaired an already-existing venv by installing the newly required validators.
- A second bootstrap run reported all requirements already satisfied.
- Ruff, yamllint, actionlint, ShellCheck, Compose contract tests, Ansible syntax and Compose rendering all passed.
- Source parity check proved local `main`, GitHub `main`, and Gitea `main` at the same commit before the publication sprint continued.
- PR #7 completed with green CI and merged to protected `main`.

Trade-offs:
- Gitea is intentionally not a second push target.
- Gitea Actions still does not receive production Docker, registry, or Kubernetes credentials.
- `actions/download-artifact@v4` still has a non-blocking Node.js runtime deprecation warning.

What I learned:
Validation quality and source convergence are separate controls. A mirror can be healthy while execution capabilities remain intentionally asymmetric, and bootstrap logic must converge dependencies rather than merely create them once.

## EVIDENCE-013: Build-Once, Verified GHCR Publication

Date: 2026-10-05

Problem:
The platform could build and test an ARM64 application but had not yet proven that the exact tested artifact could be scanned, transferred across isolated CI jobs, and published without rebuilding or over-granting registry credentials.

Implementation:
- Split application build from runtime acceptance.
- Passed one explicit commit-associated image reference through build, test and Trivy scan.
- Added vulnerability and secret scanning with an explicit CRITICAL promotion gate.
- Added generic image export, transfer-verification and publication scripts.
- Recorded Docker image ID before export.
- Recorded SHA-256 for the exported image archive.
- Uploaded/downloaded the image through GitHub Actions artifact storage.
- Verified archive checksum and Docker image ID after `docker load`.
- Isolated `packages: write` to a separate publisher job.
- Authenticated to GHCR with the job-scoped `GITHUB_TOKEN`.
- Published the verified image without rebuilding.

Verification:
- GitHub Actions run #27 completed successfully on `ubuntu-24.04-arm`.
- Transfer verification reported `image.tar: OK`.
- Docker image ID before and after job transfer matched:

```text
sha256:6778f34a5be85bfd970f9124f53efb761d12317feb15c0a4f5c2b29117a0416b
```

- Published source commit:

```text
1ddd76c14a35f974d06dbd1ed7e3c4c14475c92d
```

- Published GHCR tag:

```text
ghcr.io/ctalaveraw/platform-hello:1ddd76c14a35f974d06dbd1ed7e3c4c14475c92d
```

- GHCR reported registry digest:

```text
sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e
```

Failure-driven evidence:
- The first post-merge upload failed because `.ci-artifacts/` was hidden from the upload action by default; changing to `ci-artifacts/` fixed transfer.
- A later green run exposed that authentication alone did not imply publication because the final publish step had not yet been defined; the missing invocation was added and the next run proved the full path.

Trade-offs:
- CI artifact transfer adds temporary storage and time compared with a monolithic build/push job.
- The commit-derived tag is traceable but movable; the registry digest is the immutable identity intended for later pull/deployment.
- Local Gitea OCI replication and Kubernetes deployment are still pending.

Evidence:
- PR #5: separate build from acceptance.
- PR #6: Trivy scan of the tested image.
- PR #7: repository quality gates and source convergence tooling.
- PR #8: verified image handoff and publisher architecture.
- PR #9: artifact-path correction.
- PR #10: completed GHCR publication.
- GitHub Actions run #27: `37284420724`.
- ADR-0006.
- docs/sprints/08-application-delivery-foundation.md.

What I learned:
A promotion pipeline is not merely a sequence of successful commands. Artifact identity, integrity across trust boundaries, explicit security policy, and least-privilege credentials must all remain intact until the registry returns the immutable deployment identity.

## EVIDENCE-014: Dual OCI Distribution with Immutable Artifact Parity

Date: 2026-10-07

Problem:
The platform had produced and qualified an ARM64 artifact in GHCR, but had not
yet proven redundant OCI distribution without rebuilding the application.

Implementation:
- Added Skopeo 1.18.0 through the Ansible-managed R5C package baseline.
- Inspected the qualified GHCR artifact directly by immutable digest.
- Validated the Gitea Docker Registry v2 endpoint and Bearer authentication flow.
- Used a package-scoped Gitea credential supplied outside repository code.
- Replicated the qualified GHCR artifact directly into Gitea using digest preservation.
- Added repository-owned tooling for OCI replication, registry parity,
  complete retrieval verification and Gitea package/repository association.
- Linked the Gitea container package to the mirrored source repository.
- Hardened the package-link helper to operate idempotently by inspecting
  current package metadata before mutation.

Verification:
- A fresh GHCR retrieval by digest downloaded the manifest, configuration and
  all referenced layers.
- A fresh Gitea retrieval by digest downloaded the manifest, configuration and
  all referenced layers.
- GHCR and Gitea both reported:

```text
sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e
```

- A second replication reused existing Gitea blobs and preserved the same
  registry manifest digest.
- The Gitea package appeared associated with `admin/arm-homelab-platform`.
- Re-running the package-link helper detected the existing desired association
  and exited successfully without mutation.
- Final repository validation discovered 13 tracked shell scripts and passed
  Bash syntax, ShellCheck, Python/Ruff, YAML/yamllint, actionlint, Compose
  contracts, Ansible syntax and Compose rendering.

Failure-driven evidence:
- Re-linking an already-associated package initially returned HTTP 400
  `invalid argument`.
- Rather than treating an ambiguous 400 as success, the helper was redesigned
  to read current package state and distinguish already-linked, unlinked and
  mismatched states.

Trade-offs:
- Gitea currently uses LAN HTTP, so registry operations explicitly disable TLS
  verification for that local endpoint rather than changing global Docker
  daemon trust.
- Registry redundancy is not off-device backup.
- Matching digests establish artifact identity/integrity against the trusted
  expected digest, not build provenance or application safety.
- Package credentials remain operator/caller supplied rather than embedded in
  repository tooling.

Evidence:
- `scripts/ops/replicate-oci-image.sh`
- `scripts/ops/verify-oci-parity.sh`
- `scripts/ops/verify-oci-retrieval.sh`
- `scripts/ops/link-gitea-package.sh`
- `docs/sprints/09-dual-oci-distribution.md`

What I learned:
Artifact identity, source traceability, provenance, vulnerability state,
availability and backup are different properties. A matching immutable digest
can prove that two registries reference the same qualified artifact without
proving who built it or whether the surrounding build system is trustworthy.

## Evidence Template

### EVIDENCE-XXX: Title

Date:
Problem:
Implementation:
Verification:
Trade-offs:
Evidence:
What I learned:
