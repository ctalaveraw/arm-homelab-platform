# ADR-0015: Forgejo and Controller HTTPS Ingress

Date: 2026-11-17. Status: selected design; host acceptance pending.

## Context

The operator selected Forgejo to replace Gitea and requested a registered-domain entry point. The recorded Gitea image is 1.27.3. Forgejo's supported in-place path covers Gitea through 1.22, via Forgejo 10; it does not cover this deployment. A container image substitution against the existing database is therefore unsuitable.

OUTER provides WAN/firewall/WireGuard access and INNER provides LAN routing and DNS. The independent R5C already owns guarded management application lifecycles.

## Decision

Deploy Forgejo 15.0.11 LTS with a fresh database and separate SD-backed state. Recreate the canonical GitHub pull mirror and transfer any local-only metadata through supported application migration. Replicate OCI images with digest preservation, and register a fresh restricted Forgejo runner. Preserve legacy Gitea data and manifests until acceptance and rollback checks are complete.

Run Caddy on the controller for the initial hostname. Keep routers responsible for forwarding, firewall policy and DNS. Use an explicitly bound listener, persistent guarded certificate state, and a dedicated ingress network. Forgejo trusts only the configured Caddy container address for forwarded headers; proxy authentication remains disabled. Do not publish controller administration, cache, metrics or Docker endpoints.

Use the registered domain independently from the product name, for example `git.<domain>`. Public reachability and private LAN/WireGuard access are separate deployment choices. The supplied Caddyfile is the public ACME profile; DNS-01/private access requires provider-specific follow-up.

## Consequences

The controller becomes the initial HTTPS failure domain as well as the forge host. This is acceptable for the present single-host lab, while a dedicated ingress host remains a later move. Two instances temporarily consume additional resources and require explicit reconciliation of accounts, SSH host keys, runner identity, mirror settings, packages and clients.

No database downgrade, data-directory rename, router mutation or automatic deletion is part of the transition. Historical Gitea evidence retains its original identity. Existing source authority, GitHub CI publication and Flux application reconciliation remain in force.

This decision supersedes the optional Forgejo evaluation in ADR-0012. It does not change the independent-recovery, storage-guard or runner-authority decisions in the earlier ADRs.

## References

- [Forgejo Gitea migration](https://forgejo.org/docs/v15.0/admin/upgrade/from-gitea/)
- [Forgejo LTS releases](https://forgejo.org/releases/15.x/)
- [Migration runbook](../runbooks/gitea-to-forgejo.md)
- [Domain ingress runbook](../runbooks/domain-ingress.md)
