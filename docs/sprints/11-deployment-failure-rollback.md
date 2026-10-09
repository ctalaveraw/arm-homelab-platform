# Sprint 11 — Deployment Failure and Rollback

**Work item:** PLAT-010
**Completed:** 2026-10-09
**Status:** Complete — failed Kubernetes rollout diagnosed with service continuity preserved and rollback proven

## Objective

Prove how the platform behaves when a Kubernetes application deployment is
intentionally broken.

The sprint must demonstrate:

1. observable rollout failure;
2. preservation or loss of application availability;
3. useful diagnostic evidence;
4. recovery through Kubernetes rollback;
5. reconciliation with repository desired state after recovery.

## Baseline

`platform-hello` began healthy at Deployment revision 1.

Known-good artifact:

```text
sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e
```

State:

```text
Deployment: 1/1 Ready
ReplicaSet: platform-hello-57999d5984
Pod:        platform-hello-57999d5984-pws46
Endpoint:   10.244.3.9:8080
```

A real request through the ClusterIP Service returned the expected HTML.

## RollingUpdate behavior

The Deployment uses Kubernetes defaults:

```text
maxSurge=25%
maxUnavailable=25%
```

With one replica this permits one surge Pod and zero unavailable Ready Pods.

The expected behavior was therefore:

```text
old Ready Pod remains
        +
new replacement attempts startup
```

until the replacement becomes Ready.

## Controlled failure

Using the scoped `platform-deployer` identity, the live Deployment was changed
to a validly formatted but nonexistent OCI digest.

Git was not modified.

Kubernetes created revision 2 and ReplicaSet:

```text
platform-hello-5c65897546
```

The new Pod was scheduled successfully but the container runtime could not
retrieve the image.

Observed states:

```text
ErrImagePull
ImagePullBackOff
```

The registry lookup returned `NotFound`.

## Rollout failure

`kubectl rollout status` failed to complete within the test timeout.

At failure time:

```text
old ReplicaSet: desired=1 ready=1
new ReplicaSet: desired=1 ready=0
```

The old replica remained pending termination rather than being removed before a
Ready replacement existed.

## Endpoint and availability behavior

The EndpointSlice contained both addresses.

Known-good Pod:

```text
ready=true
serving=true
```

Failed replacement:

```text
ready=false
serving=false
```

Ten consecutive HTTP requests through the ClusterIP Service returned 200.

The failed rollout therefore did not produce an observed application outage.

## Recovery

The scoped deployer executed:

```text
kubectl rollout undo deployment/platform-hello --to-revision=1
```

Kubernetes restored the known-good Pod template.

The good ReplicaSet returned to one desired and one Ready replica.

The failed ReplicaSet scaled to zero.

The Deployment image returned to the qualified digest.

Ten post-rollback Service requests also returned HTTP 200.

## Revision semantics

After rollback, rollout history showed revisions 2 and 3 rather than restoring
the Deployment to revision number 1.

The previous good Pod template became the current Deployment revision.

This distinguishes:

```text
Deployment revision
```

from:

```text
immutable OCI artifact identity
```

The registry digest remains the authoritative artifact identifier.

## Desired-state reconciliation

The repository manifest remained unchanged during the entire exercise.

After rollback:

```text
deployment.apps/platform-hello unchanged
service/platform-hello unchanged
```

The repository-owned deployment verifier confirmed that desired and runtime
digests matched exactly.

## Repository artifact decision

No fault-injection executable was added.

Native Kubernetes rollout commands already expose the relevant mechanisms
clearly, while an executable whose purpose is to deliberately break the live
Deployment would increase accidental-execution risk.

The repeatable operational interface is instead documented as:

```text
docs/runbooks/kubernetes-deployment-rollback.md
```

## Evidence

- `docs/incidents/2026-10-09-platform-hello-failed-rollout.md`
- `docs/runbooks/kubernetes-deployment-rollback.md`
- Kubernetes rollout history
- ReplicaSet and Pod state
- kubelet image-pull Events
- EndpointSlice readiness conditions
- pre-failure, during-failure and post-rollback HTTP verification
- repository-owned deployment verification

## Acceptance

- [x] capture healthy baseline;
- [x] inject controlled deployment failure;
- [x] create a failed replacement ReplicaSet and Pod;
- [x] observe registry retrieval failure;
- [x] observe rollout timeout;
- [x] preserve previous Ready replica;
- [x] inspect Kubernetes Events;
- [x] distinguish EndpointSlice membership from endpoint readiness;
- [x] verify HTTP availability during failed rollout;
- [x] execute rollback with scoped deployment identity;
- [x] restore qualified image digest;
- [x] scale failed ReplicaSet to zero;
- [x] verify HTTP availability after rollback;
- [x] reconcile successfully with unchanged Git desired state;
- [x] record incident and recovery runbook.

**PLAT-010 functional acceptance: PASSED.**

## Next sprint — PLAT-011

Introduce Flux pull-based reconciliation after completing and understanding the
manual push-based deployment and rollback path.
