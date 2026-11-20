# ADR-0015: Forgejo and controller ingress

Date: 2026-11-17
Status: Accepted; Forgejo LAN cutover and public Zulip organization/owner login verified 2026-11-18. Private Forgejo HTTPS and remaining chat functional/recovery acceptance are separate.

## Context

The operator selected Forgejo to replace Gitea and requested public access for Zulip through a registered domain. Forgejo must remain limited to LAN/WireGuard access.

The source ran Gitea 1.27.3. Forgejo's documented in-place path covers Gitea through 1.22 via Forgejo 10, so this instance required a fresh database and application-level transfer.

OUTER provides the WAN firewall and WireGuard. INNER provides LAN routing and DNS. The R5C already manages the application services independently of Kubernetes.

## Decision

Run Forgejo 15.0.11 LTS with separate SD-backed state and a fresh restricted runner identity. Keep GitHub canonical and use a one-way pull mirror under owner `ctalaveraw`. Transfer existing OCI content with digest preservation and link the package to the mirrored repository.

Forgejo now serves `http://git.lab.home.arpa:3000/` and SSH/2223. Source parity, OCI retrieval, manual/push native validation and availability checks passed. The old Gitea units are disabled; their state, images, manifests and private backups are retained for rollback.

Public Zulip uses controller containers for the application, PostgreSQL, RabbitMQ, Redis, Memcached, Caddy and cloudflared. The connector initiates outbound tunnel connections. Its token is supplied as a file secret, and the stack publishes no host ports. Cloudflare manages public chat DNS and edge HTTPS. OUTER/INNER keep their existing responsibilities.

Caddy accepts the exact chat hostname on an internal listener. The tunnel and application use separate proxy networks. The public stack shares neither Forgejo's state nor its Docker network. Controller administration, private Git, caches, metrics and dependency ports are excluded from public routing.

The operator confirmed initialization, repeat Ansible convergence, all seven
containers running, healthy application/connector probes and public organization
creation/login. Host-side SMTP TLS/authentication passed; invitation delivery,
messages/uploads, cellular/native clients, sustained capacity and recovery remain
open in the [operator acceptance table](../runbooks/zulip-controller.md#accepted-and-pending-checks).

The separate `compose/caddy` profile is optional private Forgejo HTTPS configuration. Its reference ACME configuration needs adaptation for private DNS-01 certificates or a locally trusted CA before deployment. It is not a Cloudflare Tunnel target.

## Consequences

The R5C hosts the forge and the public chat application profile, so a controller failure can interrupt both. Resource limits and startup checks reduce the chance of overcommit, but workload capacity and restore still require live tests.

The tunnel avoids inbound web forwarding and chat DDNS. Unrelated DDNS and WireGuard configuration remain independent.

Application data was transferred between separate instances. Accounts, SSH host keys, runner registration, registry credentials and client URLs required explicit updates. Retained legacy state must be reviewed before deletion.

GitHub publication and Flux reconciliation keep their existing authority. This decision replaces the Forgejo evaluation in [ADR-0012](0012-portability-and-platform-product.md).

## References

- [Supported Gitea conversion](https://forgejo.org/docs/v15.0/admin/upgrade/from-gitea/)
- [Forgejo 15 LTS releases](https://forgejo.org/releases/15.x/)
- [Migration and rollback](../runbooks/gitea-to-forgejo.md)
- [Domain ingress](../runbooks/domain-ingress.md)
- [Controller Zulip](../runbooks/zulip-controller.md)
