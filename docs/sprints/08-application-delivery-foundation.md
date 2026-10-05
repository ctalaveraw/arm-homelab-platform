# Sprint 08 — Application Delivery Foundation

**Work item:** PLAT-007  
**Started:** 2026-10-04  
**Status:** In progress  
**Application:** `apps/platform-hello`

## Objective

Connect the existing source-control and CI foundation to a real application delivery path, while requiring enough conceptual understanding to defend each new stage in a technical interview.

The application is intentionally small. The engineering objective is the delivery chain, artifact identity, failure behavior, and eventual Kubernetes deployment.

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

## Reusable acceptance script

Created `scripts/ci/test-hello.sh`.

The script:

- fails fast with `set -euo pipefail`;
- builds an ARM64 image;
- verifies architecture and non-root runtime;
- starts a temporary container;
- polls readiness;
- verifies content;
- sends failures to stderr with a nonzero exit status;
- captures container logs on failure;
- cleans up temporary resources.

## GitHub Actions integration

The GitHub workflow now contains:

```text
validate
   |
   v
build-hello
```

`build-hello` uses `needs: validate`, so failed repository validation prevents image construction.

The validation job also runs a Docker Buildx `--check` against the application Dockerfile.

`actions/checkout` was upgraded to v5 on GitHub-hosted jobs, resolving the observed Node.js 20 deprecation warning.

Both jobs passed after merge to `main`.

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
- why a build job should depend on validation for this pipeline;
- why a hosted runner's local image disappears with the ephemeral runner;
- why an OCI registry is required for independent retrieval;
- why test/scan/publish should operate on the same built artifact.

## Current architecture boundary

Implemented:

```text
Git commit
  -> GitHub Actions validation
  -> Dockerfile check
  -> ARM64 image build
  -> non-root runtime test
  -> HTTP readiness/content acceptance
```

Pending:

```text
same tested image
  -> vulnerability scan
  -> GHCR publication
  -> immutable digest
  -> replication to Gitea OCI
  -> Kubernetes pull/deploy
```

## Next gate

Refactor application testing so it accepts an explicitly built image reference instead of performing a second build internally.

Acceptance criterion:

> One image identity is created once and carried through runtime acceptance, scan, publication, digest capture, and later deployment.

## Deferred but related

- Gitea OCI registry validation;
- Restic backup/restore of Gitea/package state;
- shared HTTPS;
- Helm packaging;
- Flux reconciliation.

These remain downstream work and should not interrupt the build/test/scan/publish learning path.
