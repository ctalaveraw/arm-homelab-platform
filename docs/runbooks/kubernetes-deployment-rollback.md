# Kubernetes Deployment Failure and Rollback Runbook

## Purpose

Diagnose and recover a failed `platform-hello` Kubernetes rollout while
preserving least privilege and verifying artifact identity after recovery.

This runbook assumes the scoped `platform-deployer` kubeconfig is available to
the operator.

## Establish identity

```bash
export KUBECONFIG="$HOME/.kube/platform-deployer/config"

kubectl auth whoami
```

Expected username:

```text
platform-deployer
```

## Inspect Deployment state

```bash
kubectl -n platform-demo get deployment platform-hello -o wide

kubectl -n platform-demo rollout history \
  deployment/platform-hello

kubectl -n platform-demo get replicasets \
  -l app.kubernetes.io/name=platform-hello \
  -o wide

kubectl -n platform-demo get pods \
  -l app.kubernetes.io/name=platform-hello \
  -o wide
```

## Determine why the rollout is failing

Identify the newest application Pod:

```bash
NEW_POD="$(
  kubectl -n platform-demo get pods \
    -l app.kubernetes.io/name=platform-hello \
    --sort-by=.metadata.creationTimestamp \
    -o jsonpath='{.items[-1:].metadata.name}'
)"

printf 'Newest Pod: %s\n' "$NEW_POD"
```

Inspect it:

```bash
kubectl -n platform-demo describe pod "$NEW_POD"
```

Inspect recent namespace Events:

```bash
kubectl -n platform-demo get events \
  --sort-by=.lastTimestamp
```

Typical image-delivery failure signals include:

```text
ErrImagePull
ImagePullBackOff
NotFound
```

## Verify Service availability

Inspect EndpointSlice readiness rather than assuming every listed address is a
serving backend:

```bash
kubectl -n platform-demo get endpointslice \
  -l kubernetes.io/service-name=platform-hello \
  -o jsonpath='{range .items[*].endpoints[*]}{.addresses[0]}{" ready="}{.conditions.ready}{" serving="}{.conditions.serving}{" terminating="}{.conditions.terminating}{" pod="}{.targetRef.name}{"\n"}{end}'
```

A failed replacement may appear in the EndpointSlice while reporting:

```text
ready=false
serving=false
```

Do not treat presence in an EndpointSlice as proof that the endpoint is
receiving normal Service traffic.

## Roll back

Review rollout history:

```bash
kubectl -n platform-demo rollout history \
  deployment/platform-hello
```

Then restore the known-good revision:

```bash
kubectl -n platform-demo rollout undo \
  deployment/platform-hello \
  --to-revision=<KNOWN_GOOD_REVISION>
```

Wait for completion:

```bash
kubectl -n platform-demo rollout status \
  deployment/platform-hello \
  --timeout=120s
```

## Verify recovery

```bash
kubectl -n platform-demo get deployment platform-hello -o wide

kubectl -n platform-demo get replicasets \
  -l app.kubernetes.io/name=platform-hello \
  -o wide

kubectl -n platform-demo get pods \
  -l app.kubernetes.io/name=platform-hello \
  -o wide
```

Verify the Deployment image:

```bash
kubectl -n platform-demo get deployment platform-hello \
  -o jsonpath='{.spec.template.spec.containers[0].image}'
echo
```

Finally reconcile against repository desired state:

```bash
KUBECONFIG="$HOME/.kube/platform-deployer/config" \
  bash scripts/ops/deploy-platform-hello.sh
```

Successful recovery requires the repository desired digest and running
container image digest to match.

## Important interpretation

`kubectl rollout undo` restores an earlier Pod template as current desired
state.

It does not guarantee that the Deployment's current revision number becomes
the historical revision number again.

Rollback creates a new point in rollout history, while the immutable OCI digest
identifies the actual application artifact.
