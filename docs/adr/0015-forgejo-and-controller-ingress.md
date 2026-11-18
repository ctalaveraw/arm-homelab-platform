# ADR-0015: Forgejo and Controller HTTPS Ingress

Date: 2026-11-17. Status: selected design; host acceptance pending.

## Context

The operator selected Forgejo to replace Gitea and requested a registered-domain entry point. The recorded Gitea image is 1.27.3. Forgejo's supported in-place path covers Gitea through 1.22, via Forgejo 10; it does not cover this deployment. A container image substitution against the existing database is therefore unsuitable.

OUTER provides WAN/firewall/WireGuard access and INNER provides LAN routing and DNS. The independent R5C already owns guarded management application lifecycles.

## Decision

Deploy Forgejo 15.0.11 LTS with a fresh database and separate SD-backed state. Recreate the canonical GitHub pull mirror and transfer any local-only metadata through supported application migration. Replicate OCI images with digest preservation, and register a fresh restricted Forgejo runner. Preserve legacy Gitea data and manifests until acceptance and rollback checks are complete.

Run Caddy on the controller. Public Zulip uses an outbound cloudflared connector and an unpublished internal Caddy listener; routers retain firewall, routing, DNS, DDNS and WireGuard roles. A future private Forgejo HTTPS listener uses separate routing/state and trusts only its configured proxy. Do not publish Forgejo, controller administration, cache, metrics or Docker endpoints through the public tunnel.

Keep public chat and private Git hostname policies separate. Cloudflare supplies public chat DNS and edge HTTPS; the controller tunnel requires no inbound web forwarding or chat DDNS. The legacy Forgejo Caddyfile is a reference ACME profile, not an authorized public Git endpoint. Private trusted certificates require DNS-01/provider-specific follow-up or a locally trusted private CA.

## Public application ingress follow-up

Public Zulip uses controller-hosted cloudflared and internal Caddy containers,
with a remotely managed token supplied as a file secret. No host web ports or
inbound router DNAT are published by that profile. Cloudflare manages the public
chat DNS/edge HTTPS; unrelated DDNS/WireGuard stays independent. Forgejo remains
private and is excluded from both public hostname routing and tunnel targets.
The public profile shares neither the private Forgejo Docker network nor its
state. Private Forgejo HTTPS remains a separate deployment choice.

See [Cloudflare Tunnel deployment](../runbooks/cloudflared.md). Real hostnames,
addresses, token values and account/tunnel identifiers stay outside Git.

## Consequences

The controller becomes the initial HTTPS failure domain as well as the forge host. This is acceptable for the present single-host lab, while a dedicated ingress host remains a later move. Two instances temporarily consume additional resources and require explicit reconciliation of accounts, SSH host keys, runner identity, mirror settings, packages and clients.

No database downgrade, data-directory rename, router mutation or automatic deletion is part of the transition. Historical Gitea evidence retains its original identity. Existing source authority, GitHub CI publication and Flux application reconciliation remain in force.

This decision supersedes the optional Forgejo evaluation in ADR-0012. It does not change the independent-recovery, storage-guard or runner-authority decisions in the earlier ADRs.

## References

- [Forgejo Gitea migration](https://forgejo.org/docs/v15.0/admin/upgrade/from-gitea/)
- [Forgejo LTS releases](https://forgejo.org/releases/15.x/)
- [Migration runbook](../runbooks/gitea-to-forgejo.md)
- [Domain ingress runbook](../runbooks/domain-ingress.md)
