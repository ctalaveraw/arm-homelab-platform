# Sprint 08 — Application Delivery Foundation

**Work item:** PLAT-007  
**Started:** 2026-10-04  
**Completed:** 2026-10-05  
**Status:** Complete — build-once security gate, verified job handoff, and GHCR publication proven  
**Application:** `apps/platform-hello`

## Objective

Connect the existing source-control and CI foundation to a real application-delivery path while requiring enough conceptual understanding to defend each stage in a technical interview.

The application is intentionally small. The engineering objective is the delivery chain, artifact identity, failure behavior, security policy, least privilege, and promotion of one verified artifact.

## Application

`platform-hello` consists of:

- a static `index.html`;
- `python:3.13-alpine` base image;
- `WORKDIR /app`;
- explicit `COPY` into the image;
- runtime UID/GID `10001:10001`;
- Python standard-library HTTP server on container port 8080.

The simple application avoids hiding delivery mechanics behind application-framework complexity.

## Local acceptance

Verified on the ARM64 R5C:

- image builds as `linux/arm64`;
- application process runs as UID 10001;
- container port 8080 is mapped only to host loopback during local tests;
- HTTP readiness required multiple polling attempts before success;
- expected HTML content returned;
- failure diagnostics are retained before cleanup.

A failed build/re-run exercise also demonstrated why a pre-existing image cannot be treated as proof that the current source built successfully.

## Build-once refactor

The original acceptance script built and tested the image in one script. PLAT-007 deliberately separated those responsibilities:

```text
build-hello.sh IMAGE
        |
        v
test-hello.sh IMAGE
        |
        v
scan-hello.sh IMAGE
```

`test-hello.sh` now refuses to proceed if the explicit image reference does not exist.

This preserves one image identity through build, runtime acceptance and scanning.

The implementation also reinforced an important hosted-CI boundary: separate GitHub Actions jobs do not share a local Docker image store, so promotion across jobs requires deliberate artifact transfer or a registry.

## Security gate

Trivy was added after runtime acceptance.

The implemented policy is:

- report UNKNOWN/LOW/MEDIUM/HIGH/CRITICAL findings for visibility;
- fail promotion on CRITICAL findings;
- scan both vulnerabilities and secrets;
- scan the exact image that already passed runtime acceptance.

The first scan passed with no vulnerability or secret findings.

The knowledge gate distinguished:

- **scanner output:** what was detected;
- **security policy:** which findings block promotion.

## Repository quality hardening

Before granting registry-write capability, repository validation was strengthened with:

- Ruff for tracked Python;
- yamllint with repository-owned policy;
- actionlint for GitHub workflow semantics;
- existing Bash syntax and ShellCheck;
- existing YAML parsing, Compose contract tests, Ansible syntax and Compose rendering.

Ruff immediately found real inconsistencies:

- four executable Python storage guards were tracked without executable mode;
- intentional `subprocess.run` return-code handling lacked explicit `check=False`;
- one import block required normalization.

The findings were corrected rather than suppressed.

CI bootstrap was also changed from “create dependencies once” to “converge required dependencies on every run,” fixing stale-venv behavior when new validators were added.

## Source and merge controls

The controller working copy added the private Gitea repository as a fetch-only remote while GitHub remained the default push destination.

`scripts/ops/check-source-parity.sh` proved:

```text
Local main == GitHub main == Gitea main
```

at the convergence point before GHCR work continued.

GitHub `main` was then protected so the “checks first, merge second” rule became an enforced platform control.

## Least-privilege promotion design

The operator selected a split-job design rather than granting registry write access to the build/test/scan job.

Implemented boundary:

```text
READ-ONLY BUILD JOB
build
  -> test
  -> scan
  -> export image
  -> record Docker image ID
  -> record archive SHA-256
  -> upload artifact

JOB / PERMISSION BOUNDARY

WRITE-SCOPED PUBLISH JOB
download artifact
  -> verify archive SHA-256
  -> docker load
  -> verify Docker image ID
  -> authenticate to GHCR
  -> publish same image
```

The build job retains `contents: read`.

Only the publisher receives:

```yaml
permissions:
  contents: read
  packages: write
```

Registry authentication uses GitHub's automatically supplied `GITHUB_TOKEN`; no manually injected PAT or registry password is required.

## Generic image-transfer scripts

Image mechanics were intentionally kept out of workflow YAML where practical.

Added:

- `scripts/ci/export-image.sh`;
- `scripts/ci/verify-image-transfer.sh`;
- `scripts/ci/publish-image.sh`.

The workflow owns triggers, job boundaries, permissions, GitHub artifact actions, and secret context. The scripts own deterministic Docker/archive/integrity mechanics.

This keeps the promotion architecture reusable when `platform-hello` is eventually replaced or joined by other applications.

## Failure-driven corrections

Two post-merge integration issues were useful rather than hidden:

### Hidden artifact directory

The first publication attempt successfully exported the image but `actions/upload-artifact` found no files because the transfer directory was named `.ci-artifacts/` and hidden-file inclusion was disabled.

Fix:

```text
.ci-artifacts/
    ->
ci-artifacts/
```

The next post-merge run proved upload, download, archive checksum verification, image loading and Docker image-ID preservation.

### Missing final publish invocation

The publisher initially authenticated successfully but the workflow stopped before invoking the existing `publish-image.sh`.

A small follow-up added the missing publish and logout steps.

This reinforced that a green workflow only proves the steps actually defined in that workflow.

## Final acceptance evidence

GitHub Actions run #27 completed successfully on the post-merge `main` commit:

```text
1ddd76c14a35f974d06dbd1ed7e3c4c14475c92d
```

The read-only build job successfully:

- validated source;
- built the ARM64 image once;
- performed HTTP runtime acceptance;
- completed Trivy scanning;
- exported and uploaded the tested/scanned image.

The separate publisher successfully:

- downloaded the artifact;
- verified `image.tar: OK`;
- loaded the image;
- matched the pre-transfer and post-transfer Docker image ID;
- authenticated with `packages: write`;
- pushed the verified image to GHCR;
- logged out.

Preserved Docker image ID:

```text
sha256:6778f34a5be85bfd970f9124f53efb761d12317feb15c0a4f5c2b29117a0416b
```

Published tag:

```text
ghcr.io/ctalaveraw/platform-hello:1ddd76c14a35f974d06dbd1ed7e3c4c14475c92d
```

Registry digest:

```text
sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e
```

**PLAT-007 functional acceptance: PASSED.**

## Knowledge gates completed

The operator demonstrated the ability to explain:

- image versus container;
- `WORKDIR` versus `COPY`;
- build context versus Dockerfile selection;
- `EXPOSE` versus the actual listening process;
- host-to-container port publishing;
- why a running container does not prove application readiness;
- why CI only sees committed source;
- fail-fast behavior and nonzero exit status;
- why a build job should depend on validation;
- why ephemeral jobs do not share a Docker image store;
- why an OCI registry is required for independent retrieval;
- why build/test/scan/publish should operate on the same artifact;
- scanner findings versus promotion policy;
- why least privilege favors a separate publisher;
- why a commit-derived tag provides traceability but a registry digest provides immutable OCI identity.

## Next sprint — PLAT-008

Dual OCI distribution.

The next gates are:

```text
GHCR artifact
  -> prove independent pull by digest
  -> validate Gitea OCI
  -> replicate the same artifact without rebuilding
  -> prove independent retrieval from both registries
```

Kubernetes deployment remains PLAT-009 and follows dual-distribution verification.

## Deferred but related

- Restic backup/restore of Gitea/package state;
- shared HTTPS;
- Helm packaging;
- Flux reconciliation;
- stronger supply-chain controls such as signing/attestation.

These remain downstream work and should not interrupt digest retrieval and dual-registry distribution.
