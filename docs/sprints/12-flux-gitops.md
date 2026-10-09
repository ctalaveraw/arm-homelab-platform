# Sprint 12 — Flux GitOps

Work item: PLAT-011
Date: 2026-10-09
Status: Complete, with post-merge live source handoff required

## Objective

Move normal `platform-hello` desired-state reconciliation from direct
operator-driven Kubernetes apply operations to pull-based GitOps while
preserving explicit bootstrap authority, least privilege and the existing
break-glass deployment path.

## Implementation

- Installed Flux CLI 2.9.6 declaratively on the NanoPi R5C through Ansible.
- Proved repeated Ansible convergence with `changed=0`.
- Generated the Flux installation using `flux install --export`.
- Installed only source-controller and kustomize-controller.
- Preserved the generated controller manifest as an upstream-derived artifact.
- Added a repository-owned Kustomize hardening overlay.
- Restricted both controllers to Flux objects in `flux-system`.
- Disabled cross-namespace Flux references.
- Disabled remote Kustomize bases.
- Configured the default reconciliation ServiceAccount as `default`.
- Removed generated RBAC subjects for controllers that are not installed.
- Retained the controller-level cluster-admin binding required for
  impersonation.
- Created `flux-system/platform-hello-reconciler`.
- Bound that identity only to application permissions in `platform-demo`.
- Kept Namespace ownership outside the application reconciliation set.
- Configured a public GitHub `GitRepository` requiring no Git credential.
- Configured the application Kustomization with `prune`, health waiting,
  bounded timeout and the scoped reconciliation identity.
- Recorded the trust model in ADR-0009.

## Authorization verification

The Flux application identity was proven able to:

- get, patch and delete the application Deployment;
- create and delete the application Service;
- read Pods.

It was proven unable to:

- read Secrets;
- mutate RBAC;
- create Namespaces;
- read Nodes;
- create Pods directly;
- use `pods/exec`;
- create Deployments outside `platform-demo`.

Delete authority is intentionally present for Flux because `prune: true`
allows Git resource removal to become runtime removal.

## Initial reconciliation

The GitRepository fetched:

```text
feat/plat-011-flux-gitops@sha1:6ceeda76f5f092b068e77430d34d8a35598cc2ed
```

The first application reconciliation completed successfully.

Flux inventory contained only:

```text
platform-demo_platform-hello__Service
platform-demo_platform-hello_apps_Deployment
```

The existing Deployment, ReplicaSet, Pod, Service, image digest and Pod IP
remained unchanged.

Managed fields showed `kustomize-controller` performing server-side Apply on
the Deployment and Service.

## Drift correction

Git declared:

```text
replicas: 1
```

The scoped external X.509 deployer changed live state to three replicas without
changing Git.

The Deployment reached three desired replicas, then Flux restored it to one
while the applied Git revision remained unchanged.

This proved runtime drift correction rather than a new desired-state rollout.

## Git-driven desired state

Commit:

```text
6787404c22c1b92e4bca9563ba1567b41445b8c7
```

changed Git desired replicas from one to two.

Both source-controller and kustomize-controller observed that exact revision,
and the Deployment converged to `2/2`.

Commit:

```text
f9c7997f93160d6d32865974cb1619ef86031053
```

restored Git desired replicas to one.

Flux converged the Deployment back to `1/1`.

## Suspend and resume

The application Kustomization was suspended.

With Git still declaring one replica, live state was changed to three replicas.

The cluster remained at three replicas for more than 90 seconds, proving that
application reconciliation was disabled even though source acquisition was a
separate controller concern.

After reconciliation was resumed, Flux restored the Deployment from three
replicas to one within the next observed reconciliation cycle.

## Operational boundary

Normal application reconciliation is now:

```text
protected GitHub main
  -> source-controller
  -> kustomize-controller
  -> scoped ServiceAccount impersonation
  -> platform-demo
```

The R5C X.509 deployment identity remains available for verification and
explicit break-glass operation.

The direct deployment script now skips mutation by default and requires an
explicit break-glass flag before applying manifests.

## Final source handoff

The committed GitRepository definition points to canonical protected `main`.

The live cluster intentionally remains on the feature branch until this PR is
merged so Flux cannot consume pre-PLAT-011 main state during acceptance.

Immediately after merge, the repository-owned GitRepository manifest must be
applied once through the privileged bootstrap path and verified to fetch the
merged `main` revision.

## Acceptance

- [x] Flux client is declarative and idempotent.
- [x] Generated controller authority was inspected before installation.
- [x] Controller install was hardened through an overlay.
- [x] Controllers are healthy.
- [x] Application reconciliation is namespace-scoped.
- [x] Positive and negative authorization boundaries were proven.
- [x] Public GitHub source was fetched without repository credentials.
- [x] Initial reconciliation caused no workload churn.
- [x] Flux ownership was verified through managed fields and inventory.
- [x] Live runtime drift was corrected.
- [x] Intentional Git desired-state change propagated to runtime.
- [x] Git desired state was restored.
- [x] Suspend prevented drift correction.
- [x] Resume restored drift correction.
- [x] Final repository source points to `main`.
- [ ] Post-merge live source handoff to `main`.

## Next

PLAT-012 introduces Prometheus and Grafana so the reconciliation system gains
first-class metrics and operational visibility.
