# ADR-0007: Digest-Pinned Kubernetes Images with IfNotPresent Pull Policy

Status: Accepted
Date: 2026-10-07

## Context

PLAT-009 introduces the first repository-defined Kubernetes deployment of a
CI-produced application artifact.

The qualified application artifact is already published and independently
retrievable from both GHCR and Gitea with the registry manifest digest:

```text
sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e
```

The initial Kubernetes deployment uses the canonical public GHCR distribution:

```text
ghcr.io/ctalaveraw/platform-hello@sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e
```

The deployment must preserve the build-once artifact identity established by
ADR-0006 while avoiding an unnecessary runtime dependency on registry
availability after the artifact has already been retrieved by a node.

Kubernetes supports three explicit image pull policies:

- `Always`;
- `IfNotPresent`;
- `Never`.

For an image specified by digest, Kubernetes defaults the pull policy to
`IfNotPresent` when the field is omitted.

The platform nevertheless needs an explicit policy because image retrieval is
part of the deployment contract rather than an incidental default.

## Decision

Reference deployable application images by immutable registry digest and set:

```yaml
imagePullPolicy: IfNotPresent
```

explicitly in the Kubernetes Deployment.

The first PLAT-009 workload therefore uses:

```yaml
image: ghcr.io/ctalaveraw/platform-hello@sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e
imagePullPolicy: IfNotPresent
```

The digest is the artifact identity.

The pull policy controls whether the node needs to retrieve that already-known
artifact again.

These are separate concerns.

## Why digest pinning is required

A mutable image tag can later resolve to different content.

A digest identifies a specific registry manifest and therefore keeps the
runtime reference tied to the qualified artifact that was previously:

1. built once;
2. runtime-tested;
3. vulnerability and secret scanned;
4. transferred across the CI job boundary with integrity verification;
5. published to GHCR;
6. replicated to Gitea without rebuilding;
7. verified to have the same registry manifest digest in both registries.

The Kubernetes deployment must consume that immutable artifact identity rather
than merely repeat a movable tag.

## Why IfNotPresent is used

`IfNotPresent` causes the kubelet/container runtime to retrieve the specified
artifact when the node does not already have it locally.

After successful retrieval, the node can reuse the locally cached
digest-addressed artifact for later container starts.

This provides two desirable properties.

### Immutable runtime identity

A cached artifact cannot silently become a different application version
because the workload reference contains the expected digest.

The cache is therefore not being trusted as a substitute for version
selection; the digest already selected the exact artifact.

### Reduced restart dependency on registry availability

Once the exact digest exists locally, restarting a Pod does not require the
registry to be reachable merely to reuse the same artifact.

This improves restart behavior during a temporary registry outage without
weakening artifact identity.

## First-deployment verification

PLAT-009 must not claim successful registry retrieval merely because a node
could have reused a pre-existing cached image.

Before the first deployment, the image inventory was inspected on both
schedulable worker nodes using containerd:

```text
ci-controller-02.lab.home.arpa
ci-controller-04.lab.home.arpa
```

Neither node contained `platform-hello`.

Therefore, whichever worker receives the first `platform-hello` Pod must
retrieve the digest-addressed artifact from the registry.

After deployment, runtime verification must prove:

1. which node received the Pod;
2. that the Pod became Ready;
3. the running container image identity;
4. the expected registry digest;
5. successful application traffic through the Service.

This distinguishes first-pull evidence from later cache reuse.

## Why Always was rejected

`imagePullPolicy: Always` does not provide a stronger application-version
identity when the image reference is already pinned by digest.

The digest determines which artifact may run.

`Always` would additionally require the container runtime to consult the
registry whenever Kubernetes launches the container, even when the exact
digest is already present locally.

Registry-side layer caching can make this efficient, but it still introduces
an avoidable registry-availability dependency into Pod restart behavior.

The platform may deliberately use `Always` in a future environment where
registry-side authorization or policy enforcement on every launch is a
requirement, but that is not the current PLAT-009 requirement.

## Why Never was rejected

`imagePullPolicy: Never` would require the image to be pre-populated on every
eligible node.

That would move image distribution outside the normal Kubernetes/container
runtime path and create additional node-bootstrap coupling.

The current platform instead expects a schedulable node to be able to retrieve
the qualified artifact when it is absent.

## Why the field is explicit instead of relying on the default

Kubernetes currently defaults digest-addressed images to `IfNotPresent`.

The Deployment still declares the value explicitly because:

- pull behavior is an intentional platform decision;
- reviewers can see the runtime policy without remembering Kubernetes
  defaulting rules;
- the desired behavior remains visible if the image-reference style changes
  later;
- Kubernetes sets `imagePullPolicy` when a Pod template is created and does not
  automatically reinterpret an existing policy merely because the image
  reference later changes.

The repository should express intentional runtime behavior rather than depend
on an implicit default for an architecture-relevant choice.

## Registry selection for the first deployment

The first PLAT-009 deployment uses the public GHCR artifact by digest.

Gitea OCI remains a proven secondary distribution containing the same
qualified manifest digest, but it currently introduces two additional runtime
concerns:

- private registry authentication;
- LAN HTTP registry configuration.

Those concerns are intentionally separated from the first Kubernetes delivery
proof so failures can be isolated to the Kubernetes deployment path itself.

A later exercise may prove Kubernetes retrieval from Gitea using the same
immutable digest.

## Consequences

Benefits:

- Kubernetes consumes the exact CI-qualified artifact;
- mutable tag drift cannot change the deployed application;
- successful nodes can restart the same artifact without requiring registry
  access every time;
- first-pull evidence can be proven independently by checking the node cache
  before deployment;
- the workload remains independent of node names and cluster topology;
- registry selection can evolve without changing application artifact
  identity.

Costs:

- cached images consume node storage until garbage collected;
- first scheduling onto a node that lacks the digest still depends on registry
  availability;
- a newly added or replacement node must retrieve the artifact before running
  it;
- `IfNotPresent` is not suitable when policy requires registry authorization
  to be revalidated on every container launch.

## Alternatives considered

### Mutable commit-derived tag

Rejected as the deployment identity because tags remain movable even when
their names provide useful source traceability.

### Digest plus Always

Provides the same immutable artifact selection but adds registry contact to
every container launch.

Not required for the current availability and trust model.

### Digest plus Never

Avoids registry access completely at runtime but requires external image
preloading and consistent cache management on every eligible node.

Rejected as unnecessary node coupling.

### Omit imagePullPolicy

Functionally valid because Kubernetes defaults a digest-addressed image to
`IfNotPresent`.

Rejected because the repository should make this operational choice explicit.

## Relationship to earlier decisions

ADR-0006 defines the build-once and verified OCI promotion model.

ADR-0007 extends that identity model into Kubernetes:

```text
CI-qualified registry digest
  -> Kubernetes Deployment references same digest
  -> node retrieves artifact when absent
  -> cached identical artifact may be reused
```

The deployment stage must not rebuild or substitute the qualified artifact.

## Follow-on work

- deploy the first digest-pinned application into Kubernetes;
- verify the scheduled node and runtime image identity;
- verify Deployment rollout and Service traffic;
- establish a scoped deployment identity for the external GitOps controller;
- later test local Gitea OCI consumption separately from the core deployment
  path;
- evaluate admission policy, image signatures and provenance attestations as
  later supply-chain controls.
