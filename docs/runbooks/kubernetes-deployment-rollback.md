# Kubernetes deployment failure and rollback

Flux owns the `platform-hello` Deployment and Service. Restore the intended image through Git for normal recovery. Use direct rollback only as an emergency procedure with reconciliation suspended.

## Establish identity

The scoped application identity can inspect and change `platform-demo`. It cannot manage Flux objects in `flux-system`.

```bash
export KUBECONFIG="$HOME/.kube/platform-deployer/config"
kubectl auth whoami
```

Expect `platform-deployer`. Flux suspension/resumption below requires a separate authorized GitOps kubeconfig. Set `GITOPS_KUBECONFIG` to that protected file; keep the identities separate.

## Inspect Deployment state

```bash
kubectl -n platform-demo get deployment platform-hello -o wide
kubectl -n platform-demo rollout history deployment/platform-hello
kubectl -n platform-demo get replicasets,pods \
  -l app.kubernetes.io/name=platform-hello -o wide
```

## Determine why the rollout is failing

```bash
NEW_POD="$(
  kubectl -n platform-demo get pods \
    -l app.kubernetes.io/name=platform-hello \
    --sort-by=.metadata.creationTimestamp \
    -o jsonpath='{.items[-1:].metadata.name}'
)"
kubectl -n platform-demo describe pod "$NEW_POD"
kubectl -n platform-demo get events --sort-by=.lastTimestamp
```

Image failures commonly report `ErrImagePull`, `ImagePullBackOff` or registry `NotFound`. Compare the Deployment's image with the approved GHCR digest.

## Verify Service availability

Inspect readiness and termination conditions:

```bash
kubectl -n platform-demo get endpointslice \
  -l kubernetes.io/service-name=platform-hello \
  -o jsonpath='{range .items[*].endpoints[*]}{.addresses[0]}{" ready="}{.conditions.ready}{" serving="}{.conditions.serving}{" terminating="}{.conditions.terminating}{" pod="}{.targetRef.name}{"\n"}{end}'
```

A listed address may have `ready=false` and receive no normal Service traffic.

## Roll back

### Normal GitOps recovery

Restore the approved image digest in `deploy/kubernetes/platform-hello/deployment.yaml` through a GitHub PR. After merge, Flux fetches the change and reconciles it. Verify the revision and workload before closing the incident.

An authorized GitOps operator can request reconciliation immediately:

```bash
flux reconcile kustomization platform-hello --with-source \
  --namespace flux-system \
  --kubeconfig "${GITOPS_KUBECONFIG:?Set the authorized GitOps kubeconfig}"
```

### Emergency direct rollback

Suspend reconciliation using the authorized GitOps identity first:

```bash
flux suspend kustomization platform-hello --namespace flux-system \
  --kubeconfig "${GITOPS_KUBECONFIG:?Set the authorized GitOps kubeconfig}"
```

With the scoped application identity still in `KUBECONFIG`, select a known-good revision from rollout history and set `KNOWN_GOOD_REVISION`:

```bash
kubectl -n platform-demo rollout undo deployment/platform-hello \
  --to-revision="${KNOWN_GOOD_REVISION:?Set the verified rollout revision}"
kubectl -n platform-demo rollout status deployment/platform-hello --timeout=120s
```

Verify the recovered image digest and readiness. Then restore that digest in Git through a PR. Wait until the Git source reports the corrected revision before resuming reconciliation; otherwise Flux can reapply the failed image.

```bash
flux get sources git arm-homelab-platform --namespace flux-system \
  --kubeconfig "${GITOPS_KUBECONFIG:?Set the authorized GitOps kubeconfig}"
```

Once the source revision matches the approved correction, resume:

```bash
flux resume kustomization platform-hello --namespace flux-system \
  --kubeconfig "${GITOPS_KUBECONFIG:?Set the authorized GitOps kubeconfig}"
```

## Verify recovery

```bash
kubectl -n platform-demo rollout status deployment/platform-hello --timeout=120s
kubectl -n platform-demo get deployment platform-hello -o wide
kubectl -n platform-demo get deployment platform-hello \
  -o jsonpath='{.spec.template.spec.containers[0].image}'
echo
KUBECONFIG="$HOME/.kube/platform-deployer/config" \
  bash scripts/ops/deploy-platform-hello.sh
```

The helper defaults to verification mode. `BREAK_GLASS_RECONCILE=true` enables direct apply and is reserved for explicit recovery while Flux is suspended.

A successful recovery has the approved Git digest running, ready Service endpoints and active Flux reconciliation. `rollout undo` creates a new revision; the image digest identifies the recovered artifact.

## References

- [Flux suspension](https://fluxcd.io/flux/cmd/flux_suspend_kustomization/)
- [Flux resumption](https://fluxcd.io/flux/cmd/flux_resume_kustomization/)
- [Flux reconciliation](https://fluxcd.io/flux/cmd/flux_reconcile_kustomization/)
- [Original failure exercise](../incidents/2026-10-09-platform-hello-failed-rollout.md)
