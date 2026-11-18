# Architecture decisions and implementation requirements

Approved direction: 2026-10-10. Reviewed: 2026-11-18.

Forgejo is deployed under [ADR-0015](../adr/0015-forgejo-and-controller-ingress.md). Source parity, OCI retrieval and native validation passed; the [migration checklist](../runbooks/gitea-to-forgejo.md#9-acceptance-and-retention) tracks retained legacy state and remaining review. Portal adoption is optional.

| Gate | Adopted decision | Requirement |
| --- | --- | --- |
| DG-01 | ARM-first, with optional secondary targets | Keep target inventory and adapters separate from shared policy |
| DG-02 | Separate local operations runner | Keep host, deployment and administrator credentials out of the validation runner |
| DG-03 | Reviewed PR → validation → approved Ansible operation | Require explicit authorization for infrastructure changes |
| DG-04 | Independent encrypted recovery material; OpenBao for routine secrets | Recovery must work while OpenBao or Forgejo is unavailable |
| DG-05 | Staged security enforcement | Record thresholds, exceptions, owners and expiry; verify each enforcement change |
| DG-06 | Four-hour RTO and one-hour RPO targets | Define critical state and prove the targets in timed restore exercises |
| DG-07 | Forgejo migrated separately; portal remains optional | Keep the verified forge independent of portal adoption |
| DG-08 | Planning updates track implementation status | Close work only when its required checks pass |

## Recovery and identity

Decide the critical service/data scope, backup destinations, encryption-key custody, spare target and network prerequisites. Define the incident clock and acceptable data loss before measuring the recovery targets.

Specify CA ownership, issuer access, certificate enrollment/renewal/revocation and protected kubeadm/etcd/Flux recovery assets. Keep private keys in protected recovery storage.

A future operations runner needs a distinct execution identity, reviewed workflow source, restricted playbooks/arguments, approval records, concurrency control, timeouts and an independent recovery path.

## Delivery and host configuration

Choose how verified image digests enter Git desired state and how signatures/provenance are checked. Flux remains the application reconciler.

Define admission rollout, exceptions, test namespaces, Pi resource budgets and bootstrap network access before enforcing runtime policies.

Classify local configuration and secrets, including file injection, ownership, backup and trusted CAs. Complete APT cache source ACL and bypass tests before depending on the cache during fourth-Pi bootstrap.

## Remaining deployment choices

Private Forgejo HTTPS needs its own certificate and access checks. Retiring the retained Gitea state requires the remaining [migration review](../runbooks/gitea-to-forgejo.md#9-acceptance-and-retention).

A second target needs a defined minimum environment, inventory, providers and credentials. Evaluate a developer portal only when several services or users need a catalog, templates or self-service workflows.

## Change control

Revise an ADR when operational evidence changes its assumptions. Record the required test tier and result for each implementation milestone.
