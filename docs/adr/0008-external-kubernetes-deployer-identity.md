# ADR-0008: External Kubernetes Deployment Identity Uses X.509 and Namespace-Scoped RBAC

Status: Accepted
Date: 2026-10-08

## Context

PLAT-009 requires the independent R5C management controller to deploy
applications directly to the existing kubeadm Kubernetes cluster.

The initial deployment proof used SSH to the control-plane host and the
existing `kubernetes-admin` identity. That path was suitable for bootstrap and
discovery but is too privileged for routine application delivery.

The external management controller requires its own Kubernetes identity with:

- no dependency on kubeadm `admin.conf`;
- no cluster-admin privileges;
- no ability to modify its own RBAC;
- no authority outside the application namespace;
- credentials that remain outside the public repository.

Two practical authentication approaches were considered:

1. a Kubernetes API client certificate;
2. a long-lived ServiceAccount bearer token.

## Decision

Use an X.509 Kubernetes API client certificate for the external
`platform-deployer` identity.

The client certificate:

- uses `CN=platform-deployer`;
- is signed by the Kubernetes
  `kubernetes.io/kube-apiserver-client` signer;
- currently requests a 90-day lifetime;
- is backed by a private key generated and retained only on the R5C;
- is approved explicitly through the Kubernetes CSR API;
- is stored as host-local security material outside Git.

The R5C uses a dedicated kubeconfig rather than kubeadm `admin.conf`.

Authorization is implemented separately through a namespace-scoped Role and
RoleBinding in `platform-demo`.

## Authorization boundary

`platform-deployer` may:

- create, update and patch Deployments in `platform-demo`;
- create, update and patch Services in `platform-demo`;
- read Deployments, Pods, ReplicaSets, EndpointSlices and Events required for
  deployment verification.

It may not:

- create namespaces;
- deploy into `default` or other namespaces;
- read Secrets;
- modify Roles or RoleBindings;
- read Nodes;
- create Pods directly;
- execute commands in Pods;
- delete the application Deployment.

The deployment identity therefore cannot expand its own authority.

## Verification

The Role and RoleBinding were first tested using Kubernetes impersonation
before any client credential was issued.

Positive authorization checks passed for the required deployment and
observation operations.

Negative checks confirmed denial of:

- namespace creation;
- Deployment creation outside `platform-demo`;
- Secret reads;
- RBAC mutation;
- Node reads;
- Deployment deletion;
- direct Pod creation;
- `pods/exec`.

A 3072-bit RSA private key and CSR were then generated on the R5C.

The CSR:

```text
CN=platform-deployer
signer=kubernetes.io/kube-apiserver-client
requested duration=90d
usage=client auth
```

was explicitly approved and issued by Kubernetes.

The resulting certificate:

- validated against the Kubernetes cluster CA;
- authenticated directly from the R5C to `https://10.0.0.5:6443`;
- returned `platform-deployer` from `kubectl auth whoami`;
- reproduced the expected positive and negative authorization matrix without
  impersonation.

No kubeadm administrator credential was copied to the R5C.

## Why X.509 was chosen

X.509 maps naturally to an external machine identity.

The private key can be generated locally and never leave the management
controller.

The Kubernetes CSR API also creates an explicit privileged approval boundary
between:

```text
identity requests access
```

and:

```text
cluster administrator authorizes that identity
```

A certificate has a finite validity period rather than relying on an
indefinitely valid bearer credential.

## Why a long-lived ServiceAccount token was not chosen

A ServiceAccount token can authenticate an external client and would work with
the same RBAC model.

It was not selected for this management-controller identity because:

- it is a bearer secret rather than proof of possession of a private key;
- a copied token is immediately usable by whoever possesses it;
- the external host is not itself a Kubernetes workload requiring native
  ServiceAccount identity;
- the CSR and certificate model provides an explicit issuance and expiry
  lifecycle suitable for this external management client.

This decision does not prohibit ServiceAccounts for workloads running inside
Kubernetes.

## Credential ownership

Repository and Ansible code may manage:

- Kubernetes client tooling;
- public RBAC definitions;
- protected directory scaffolding;
- deployment and verification logic.

The public repository must not contain:

- client private keys;
- issued client certificates when treated as host-local credential state;
- bearer tokens;
- kubeadm administrator kubeconfigs;
- cluster CA private keys.

## Consequences

Benefits:

- routine deployment no longer requires SSH to the control-plane host;
- the R5C does not receive cluster-admin authority;
- RBAC limits blast radius to the intended namespace;
- the deployer cannot modify its own authorization;
- authentication and authorization can be tested independently;
- credentials have an explicit expiration.

Costs:

- certificate issuance and rotation have operational lifecycle work;
- Kubernetes CSR approval requires privileged cluster access;
- an expired certificate stops deployment until renewed;
- certificate revocation is less immediate than deleting a bearer credential.

## Credential lifecycle and bootstrap role

The first client certificate was bootstrapped manually to prove the complete
authentication and authorization model before introducing credential-lifecycle
automation.

Routine R5C baseline convergence deliberately does not issue or approve
Kubernetes credentials because doing so would couple independent
management-host reconstruction to availability of the Kubernetes cluster.

The scoped X.509 identity established by PLAT-009 is therefore retained as an
independent bootstrap and recovery path.

Routine deployment credentials may later be replaced by shorter-lived,
dynamically issued Kubernetes credentials through OpenBao. PLAT-016 will
evaluate the OpenBao Kubernetes secrets engine for that purpose while
preserving the independent X.509 bootstrap path.

This avoids requiring OpenBao in order to bootstrap or recover the management
controller while also avoiding unnecessary long-term dependence on manual
client-certificate rotation for normal deployment operations.

## Relationship to ADR-0003

ADR-0003 keeps the R5C management plane independent of Kubernetes.

Ansible therefore owns the Kubernetes client capability but does not require a
live Kubernetes cluster to converge the ordinary R5C baseline.

Cluster-dependent deployment credential bootstrap is a separate operation.

## Follow-on work

- add repository-owned direct deployment and verification commands;
- retain the scoped X.509 path for bootstrap and recovery;
- evaluate OpenBao-leased Kubernetes credentials for routine deployment under
  PLAT-016;
- define how the external management controller authenticates to OpenBao;
- preserve short credential lifetimes and least-privilege Kubernetes RBAC;
- automate X.509 rotation only if the bootstrap credential's operational
  lifecycle requires it.
