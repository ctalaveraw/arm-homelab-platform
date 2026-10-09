# ADR-0009: Flux Reconciles Applications from Canonical Git with Scoped Kubernetes Authority

Status: Accepted
Date: 2026-10-09

## Context

PLAT-011 moves application delivery from explicit operator-driven Kubernetes
reconciliation toward pull-based GitOps reconciliation.

Before Flux, the NanoPi R5C used a scoped X.509 identity to apply the
repository-defined `platform-hello` Deployment and Service directly.

That path proved:

- immutable artifact delivery;
- least-privilege Kubernetes authorization;
- rollout verification;
- controlled deployment failure;
- manual rollback;
- reconciliation back to Git desired state.

The next step is to make Git desired state continuously authoritative without
turning the application reconciliation path into unrestricted cluster-admin
access.

## Decision

GitHub remains the canonical source repository.

Flux reads the public GitHub repository over HTTPS without Git credentials.

Gitea remains a private one-way mirror and is not the initial Flux source.
This avoids coupling Kubernetes reconciliation to availability of the
out-of-cluster R5C management plane.

The initial Flux installation includes only:

- source-controller;
- kustomize-controller.

Helm, notification and image-automation controllers are deferred until they
have explicit platform requirements.

## Bootstrap boundary

Flux installation is a privileged bootstrap operation.

The repository contains the generated Flux installation manifests and a local
hardening overlay, but installation remains an explicit administrator action.

PLAT-011 does not introduce a privileged Flux self-management Kustomization.

This intentionally avoids making ordinary public Git changes a direct
cluster-admin configuration path.

The privileged bootstrap layer owns:

- Flux CRDs;
- Flux controller Deployments;
- Flux controller cluster RBAC;
- the `flux-system` namespace;
- application reconciliation ServiceAccounts and RBAC;
- initial Flux Source and Kustomization objects.

## Controller hardening

The generated Flux installation is preserved as an upstream-derived artifact
and modified through a repository-owned Kustomize overlay.

The overlay:

- restricts source-controller to its own namespace;
- restricts kustomize-controller to its own namespace;
- disables cross-namespace Flux references;
- disables remote Kustomize bases;
- sets the default reconciliation ServiceAccount to `default`;
- removes generated RBAC subjects for controllers that are not installed.

The `default` ServiceAccount receives no application-management authority.

A Flux Kustomization that omits an explicit ServiceAccount therefore fails
closed instead of silently reconciling application resources as cluster-admin.

The kustomize-controller itself retains its generated cluster-admin binding
because Kubernetes impersonation is performed by that controller.

## Application reconciliation authority

`platform-hello` reconciliation uses a dedicated ServiceAccount:

```text
flux-system/platform-hello-reconciler
```

A RoleBinding grants that identity authority only inside:

```text
platform-demo
```

It may reconcile the Deployment and Service required by the application.

It may read Pods, ReplicaSets, EndpointSlices and Events for reconciliation
and operational visibility.

It may not:

- read or mutate Secrets;
- alter RBAC;
- alter Namespaces;
- access Nodes;
- create Pods directly;
- use pods/exec;
- modify CRDs;
- mutate resources outside `platform-demo`.

The automated Flux reconciler receives delete authority for the Deployment and
Service because `prune: true` makes removal from Git an intentional desired
state transition.

The existing X.509 `platform-deployer` identity remains more restrictive and
does not gain delete authority.

## Namespace ownership

The existing `platform-demo` Namespace is not part of the application
Kustomize resource set.

Namespace creation and deletion remain privileged bootstrap operations.

Flux reconciles only the application Deployment and Service.

## Lifecycle behavior

The application Flux Kustomization uses:

- immutable application image digest;
- `prune: true`;
- `wait: true`;
- bounded reconciliation timeout;
- a dedicated scoped ServiceAccount;
- `deletionPolicy: Orphan`.

Removing an application-owned resource from Git may therefore prune that
resource.

Deleting the Flux Kustomization itself does not automatically delete the
application workload.

## Operational model

After PLAT-011, normal application desired-state changes flow through:

```text
Git change
  -> protected PR / CI
  -> merge to canonical main
  -> Flux source reconciliation
  -> scoped Kubernetes reconciliation
```

The R5C X.509 deployment path remains available for break-glass operation,
verification and recovery rather than normal application delivery.

## Consequences

Benefits:

- Git becomes continuously authoritative for application desired state;
- manual cluster drift can be detected and corrected;
- Git access requires no stored repository credential for the public source;
- application reconciliation remains namespace-scoped;
- accidental omission of an application ServiceAccount fails closed;
- loss of the R5C does not remove Flux's ability to read canonical GitHub.

Costs and limitations:

- Flux introduces privileged in-cluster controllers and CRDs;
- bootstrap still requires explicit administrator authority;
- controller installation and tenant RBAC are not yet self-managed by Flux;
- GitHub availability becomes part of the normal desired-state update path;
- observability and alerting for reconciliation failures remain future work.

## Follow-on work

PLAT-011 must prove:

- initial successful Git reconciliation;
- correction of live cluster drift;
- propagation of an intentional Git desired-state change;
- Flux suspend and resume behavior;
- scoped reconciliation permissions in practice.

PLAT-012 and PLAT-013 will add observability and runtime alerting around the
resulting reconciliation system.
