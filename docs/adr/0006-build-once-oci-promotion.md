# ADR-0006: Build Once and Promote OCI Artifacts with Least Privilege

Status: Accepted  
Date: 2026-10-05

## Context

The first application delivery path must prove that the artifact tested in CI is the artifact later scanned and published.

Rebuilding between stages would create a second artifact whose contents could drift because of base-image changes, package changes, build-environment differences, or operator error.

At the same time, granting registry-write credentials to the build/test environment would unnecessarily increase blast radius.

GitHub-hosted jobs are ephemeral and do not share a local Docker image store, so a separate publisher requires an explicit handoff mechanism.

## Decision

Use a build-once promotion model.

The read-only build job:

1. builds one explicit ARM64 image;
2. runtime-tests that exact image;
3. scans that exact image;
4. records its Docker image ID;
5. exports it with `docker save`;
6. records a SHA-256 checksum for the archive;
7. uploads the archive as a short-retention CI artifact.

A separate publisher job:

1. receives `packages: write`;
2. downloads the artifact;
3. verifies the archive checksum;
4. loads the image;
5. verifies the loaded Docker image ID equals the pre-transfer ID;
6. authenticates to GHCR with the job-scoped `GITHUB_TOKEN`;
7. tags and pushes the verified image;
8. records the registry digest from publication output.

The publisher must not rebuild the image.

Workflow YAML owns orchestration, triggers, GitHub artifact actions, permission boundaries, and credential context.

Repository scripts own deterministic image export, transfer verification, and publication mechanics.

## Security policy

The current Trivy promotion policy is:

- report all configured severities;
- block promotion on CRITICAL findings;
- scan vulnerabilities and secrets.

This policy is intentionally explicit and can be tightened later without changing the artifact-identity model.

## Artifact identities

Three related identities are intentionally distinguished:

### Commit-derived tag

Example:

```text
ghcr.io/ctalaveraw/platform-hello:1ddd76c14a35f974d06dbd1ed7e3c4c14475c92d
```

Provides source traceability but remains a tag and is therefore movable.

### Docker image ID

Example:

```text
sha256:6778f34a5be85bfd970f9124f53efb761d12317feb15c0a4f5c2b29117a0416b
```

Used to prove that the image reconstructed on the publisher runner matches the image exported after test/scan.

### Registry manifest digest

Example:

```text
sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e
```

Identifies the OCI manifest stored in GHCR and is the immutable identity intended for later retrieval and Kubernetes deployment.

These hashes identify different objects and are not expected to be equal.

## Consequences

Benefits:

- tested/scanned artifact identity survives the job boundary;
- the publisher receives the minimum additional registry permission;
- pull-request validation does not receive registry write authority;
- the promotion mechanics are reusable for future applications;
- failures in transfer integrity stop publication.

Costs:

- the exported image consumes temporary CI artifact storage;
- promotion requires explicit save/upload/download/load steps;
- the pipeline is slightly slower than a monolithic single-job push.

## Verification

GitHub Actions run #27 successfully proved:

- build/test/scan on hosted ARM64;
- archive upload/download;
- archive checksum verification;
- Docker image-ID preservation across runners;
- scoped GHCR authentication;
- successful publication;
- registry digest capture.

## Follow-on work

- prove independent pull from GHCR by digest;
- validate Gitea OCI;
- replicate the same verified OCI artifact without rebuilding;
- prove retrieval from both registries;
- deploy to Kubernetes by immutable digest;
- evaluate signing/attestation only after the core dual-distribution path is proven.
