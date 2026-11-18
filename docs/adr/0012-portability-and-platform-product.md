# ADR-0012: ARM-first reference platform with opt-in secondary targets and developer portal

Status: Accepted for target architecture
Date: 2026-10-10

## Decision

Keep the current physical ARM64 reference implementation and proven delivery path intact. Define target contracts (inventory, image architecture, bootstrap and application ownership, secrets, policy, DNS, storage, test tiers) so a later Proxmox environment can exercise the same platform workflows.

An eventual Proxmox/Terraform layer creates VM/network resources; Ansible converges guest OS/management components; Kubernetes bootstrap and Flux remain their respective responsibilities. Terraform must not become a second owner of Ansible-managed service state or Flux-managed workloads. Isolate Terraform state, locking, backend credentials and drift checks by environment. Do not make a local Terraform provider a prerequisite for physical Pi support.

Forgejo is selected under [ADR-0015](0015-forgejo-and-controller-ingress.md). Use a separate instance with verified data transfer, new runner identity, package parity and rollback. The earlier Gitea acceptance remains historical. Keep canonical GitHub and independent recovery material.

Evaluate Backstage or other internal developer portal only when multiple services/personas justify a catalog, templates and self-service golden paths. Portal loss may not prevent core operation, bootstrap or recovery. Prefer documented CLI/golden-path conventions before adopting a large portal.

## Evidence required

Second target running the same build-once/digest verification and policy contracts; target-specific differences isolated; two-target pipeline validation; intentional loss of noncritical portal/provider does not break the platform; isolated Forgejo compatibility report with tested rollback.

## Consequences

Portability has a maintenance cost, so it remains an **opt-in target**, not a requirement to generalize every ARM-specific implementation now. Existing Kubernetes, Gitea and R5C remain primary proven environments.
