# Sprint 09 — Dual OCI Distribution

**Work item:** PLAT-008
**Completed:** 2026-10-07
**Status:** Complete — identical verified OCI artifact proven in external and local registries

## Objective

Extend the build-once artifact path beyond the canonical external registry
without rebuilding the application.

The sprint must prove that the artifact already qualified by CI can be:

1. independently retrieved from GHCR by immutable digest;
2. replicated into the local Gitea OCI registry;
3. preserved with the same registry manifest digest;
4. independently retrieved from Gitea by immutable digest;
5. associated with the mirrored source repository;
6. managed using repeatable repository-owned operational tooling.

## Qualified artifact

Source image:

```text
ghcr.io/ctalaveraw/platform-hello@sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e
```

The artifact is Linux ARM64.

## R5C OCI tooling

Skopeo 1.18.0 was added to the Ansible-managed common package baseline.

The first Ansible execution installed the new package and reported one change.
A subsequent execution reported:

```text
changed=0
failed=0
```

This proves the additional host capability remains declarative and idempotent.

## Independent GHCR retrieval

The R5C inspected the GHCR image directly by immutable digest.

The registry reported:

```text
sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e
```

A fresh Skopeo copy into a temporary OCI layout successfully retrieved the
manifest, configuration and all referenced layers.

This proves retrieval from the registry rather than reliance on a local Docker
cache.

## Gitea OCI discovery and authentication

The local Gitea registry endpoint responded at:

```text
http://gitea.lab.home.arpa:3000/v2/
```

Unauthenticated probing returned:

```text
HTTP/1.1 401 Unauthorized
Docker-Distribution-Api-Version: registry/2.0
```

with a Bearer authentication challenge.

A package-scoped Gitea credential successfully authenticated to the registry.
Credential material remains external to repository scripts.

## Identity-preserving replication

Skopeo copied the qualified GHCR artifact directly into Gitea.

No source checkout, Docker build or application rebuild occurred during
replication.

Replication used digest preservation and produced:

```text
GHCR:
sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e

Gitea:
sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e
```

The registry manifest identities match.

The destination also reported the same referenced layer digests as the GHCR
artifact.

## Independent Gitea retrieval

The Gitea artifact was then addressed directly by immutable digest and copied
into a fresh temporary OCI layout.

The operation successfully retrieved the manifest, configuration and all
referenced layers.

This distinguishes two separate properties:

- **identity parity:** both registries report the same manifest digest;
- **retrievability:** each registry can independently serve the complete
  referenced artifact.

## Repeat promotion

The same artifact was replicated to Gitea a second time.

Existing blobs were reported as already present and therefore reused. After
the repeated operation, registry parity still reported:

```text
Source digest:      sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e
Destination digest: sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e
```

Repeated promotion therefore did not change the qualified artifact identity.

## Gitea package/repository association

The copied container package initially existed under the Gitea package owner
without an association to the mirrored repository.

The Gitea package API linked:

```text
admin/container/platform-hello
```

to:

```text
admin/arm-homelab-platform
```

The package now appears with the mirrored source repository.

A repeated link request initially exposed non-idempotent API behavior:
attempting to create an already-existing association returned HTTP 400.

The repository-owned link helper was corrected to read current package state
first.

Its final behavior is:

```text
desired link already exists
  -> PASS without mutation

package is unlinked
  -> create link

package is linked elsewhere
  -> fail closed
```

## Repository-owned operational tooling

PLAT-008 added:

- `scripts/ops/replicate-oci-image.sh`
- `scripts/ops/verify-oci-parity.sh`
- `scripts/ops/verify-oci-retrieval.sh`
- `scripts/ops/link-gitea-package.sh`

Responsibilities remain separated.

### replicate-oci-image.sh

Copies an existing OCI artifact between registries with digest preservation.

It performs no build and contains no embedded credentials.

### verify-oci-parity.sh

Reads source and destination registry manifest digests and fails if they
differ.

### verify-oci-retrieval.sh

Copies the referenced artifact into a fresh temporary OCI layout to prove that
the registry can serve the manifest, configuration and layers.

### link-gitea-package.sh

Manages Gitea-specific package/repository metadata independently of OCI
artifact replication.

Authentication is supplied by the caller.

## Validation

All four operational scripts passed:

- Bash syntax validation;
- ShellCheck;
- real registry execution where applicable.

After the new files were staged, full repository validation discovered:

```text
Shell files: 13
```

and completed successfully across:

- Bash syntax;
- ShellCheck;
- Python parsing;
- Ruff;
- YAML parsing;
- yamllint;
- actionlint;
- Compose safety contracts;
- Ansible syntax;
- Compose rendering.

## Knowledge gates

The sprint reinforced the distinction between source traceability, artifact
identity, integrity, provenance, security, availability and recovery.

### Source traceability

A commit-derived tag helps answer:

> Which source revision was associated with this build?

### Artifact identity and integrity

An immutable registry digest helps answer:

> Which exact registry artifact is being referenced?

Matching trusted digest identities provide content-integrity evidence but do
not independently prove:

- who performed the build;
- that the source was trustworthy;
- that CI was uncompromised;
- that the image contains no malicious or vulnerable behavior;
- registry availability;
- backup/recovery capability.

Those are separate provenance, security, availability and recovery concerns.

## Acceptance

PLAT-008 acceptance criteria:

- [x] independently retrieve GHCR artifact by digest;
- [x] validate Gitea built-in OCI registry;
- [x] replicate verified artifact without rebuilding;
- [x] preserve registry manifest identity;
- [x] independently retrieve complete artifact from both registries;
- [x] associate Gitea package with mirrored repository;
- [x] encode operations in repository-owned tooling;
- [x] prove repeated package-link operation is idempotent;
- [x] full repository validation passes with the new scripts tracked.

**PLAT-008 functional acceptance: PASSED.**

## Next sprint — PLAT-009

Deploy the CI-produced artifact into the existing Raspberry Pi kubeadm cluster
using an immutable registry digest.

Initial acceptance targets:

```text
known registry digest
  -> Kubernetes Deployment
  -> container runtime pull
  -> Ready Pod
  -> running image identity verification
  -> Service/HTTP endpoint verification
```

Helm and Flux remain deliberately downstream until the raw digest-pinned
deployment path is understood and proven.
