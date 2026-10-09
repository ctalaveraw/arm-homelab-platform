# INC-002 — Controlled Kubernetes Deployment Failure

Date: 2026-10-09
Classification: Planned fault-injection exercise
Outcome: Service availability preserved; rollback completed successfully

## Objective

Validate Kubernetes Deployment failure behavior, diagnostic evidence, Service
continuity and rollback using the namespace-scoped external deployment
identity established during PLAT-009.

The exercise deliberately changed only live cluster state. Git remained the
known-good desired state throughout the incident.

## Baseline

Application:

```text
platform-hello
```

Namespace:

```text
platform-demo
```

Healthy image:

```text
ghcr.io/ctalaveraw/platform-hello@sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e
```

Initial state:

```text
Deployment:   1/1 Ready
Revision:     1
ReplicaSet:   platform-hello-57999d5984
Pod:          platform-hello-57999d5984-pws46
Pod IP:       10.244.3.9
Service IP:   10.101.39.146
HTTP:         200
```

The Deployment used the default RollingUpdate strategy:

```text
maxSurge=25%
maxUnavailable=25%
```

For one desired replica this permits one surge replica while allowing zero
Ready replicas to become unavailable.

## Fault injection

The scoped `platform-deployer` identity changed the live Deployment image to a
syntactically valid but nonexistent registry digest:

```text
sha256:0000000000000000000000000000000000000000000000000000000000000001
```

Kubernetes created Deployment revision 2 and ReplicaSet:

```text
platform-hello-5c65897546
```

A replacement Pod was scheduled to:

```text
home-phy-srv-deb-ci-controller-02
```

The registry returned `NotFound`.

The Pod progressed through:

```text
ErrImagePull
ImagePullBackOff
```

Kubelet Events recorded repeated failed image retrieval attempts.

## Rollout behavior

The new ReplicaSet remained:

```text
DESIRED=1
READY=0
```

while the previous ReplicaSet remained:

```text
DESIRED=1
READY=1
```

`kubectl rollout status` timed out with the old replica still pending
termination.

This demonstrated that Kubernetes did not terminate the only Ready
application replica while its replacement was unable to become Ready.

## Service continuity

During the failed rollout, the EndpointSlice contained both Pods.

The original Pod reported:

```text
10.244.3.9
ready=true
serving=true
terminating=false
```

The failed replacement reported:

```text
10.244.1.69
ready=false
serving=false
terminating=false
```

Ten consecutive requests through the ClusterIP Service returned HTTP 200:

```text
10 / 10 successful
```

The failed replacement therefore existed in EndpointSlice state but was not an
eligible Ready/serving backend for normal Service traffic.

## Recovery

The same scoped external deployment identity executed:

```text
kubectl rollout undo deployment/platform-hello --to-revision=1
```

The rollback completed successfully.

The known-good ReplicaSet returned to current desired state and the failed
ReplicaSet scaled to zero:

```text
platform-hello-57999d5984   DESIRED=1 READY=1
platform-hello-5c65897546   DESIRED=0 READY=0
```

The Deployment again referenced:

```text
sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e
```

Ten additional ClusterIP requests returned HTTP 200 after rollback.

## Revision behavior

Rollback did not restore the Deployment object to historical revision number
1.

Instead, Kubernetes promoted the previous Pod template as a new current
Deployment revision.

The good ReplicaSet was reused and became the current revision while the bad
ReplicaSet remained as historical rollout state.

This demonstrates that Deployment revisions describe rollout history rather
than immutable application release identifiers.

The OCI digest remains the authoritative application artifact identity.

## Git reconciliation

The repository manifest was never modified during fault injection.

After rollback, the repository-owned deployment interface reported:

```text
deployment.apps/platform-hello unchanged
service/platform-hello unchanged
```

and verified:

```text
desired digest == runtime digest
```

This proves that recovered runtime state once again matched Git desired state.

## Detection

The failure was detected through native Kubernetes signals:

- rollout timeout;
- Pod `ErrImagePull`;
- Pod `ImagePullBackOff`;
- registry `NotFound`;
- Deployment/ReplicaSet state;
- Kubernetes Events;
- EndpointSlice readiness conditions.

Automated runtime alerting is intentionally deferred to PLAT-013.

## Outcome

The exercise proved:

- a bad immutable image reference cannot complete rollout;
- the previous Ready application replica remains available;
- unready replacement Pods are excluded from normal Service traffic;
- the scoped deployment identity can perform rollback without cluster-admin;
- native Deployment rollback restores the known-good Pod template;
- repository desired state and recovered runtime state converge cleanly.

No application outage was observed during the controlled failure.
