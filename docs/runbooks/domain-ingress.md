# Domain and HTTPS ingress

Status: controller tunnel configuration prepared; real hostname, backend and
live acceptance remain pending. Forgejo stays LAN/WireGuard-only.

## Selected public application path

Use [Cloudflare Tunnel in Docker](cloudflared.md) and the
[controller public ingress guide](controller-public-ingress.md):

Cloudflare edge → controller cloudflared container → internal Caddy → Zulip.

The `compose/caddy-public` project publishes no host web/admin/metrics ports.
The first playbook run prepares files only; token entry is hidden and activation
is explicit. Use a remotely managed tunnel token file, not a token in a command
or environment. Real hostname, backend, Docker network values and Cloudflare
account/tunnel details stay local or in Cloudflare.

| Responsibility | Selected behavior |
| --- | --- |
| Public DNS/HTTPS | Cloudflare tunnel-managed chat record and edge certificate |
| Controller | Outbound connector and exact-host Caddy reverse proxy |
| OUTER/INNER | Existing routing/firewall, DNS, WireGuard and unrelated DDNS |
| Chat LAN DNS | Resolve the public Cloudflare endpoint initially |
| Application backend | Restricted endpoint reachable only by controller Caddy |

No inbound TCP 80/443 forwarding, residential chat DDNS, router application
installation or direct chat-to-controller DNS override is needed by this path.
Leave unrelated DDNS/WireGuard configuration unchanged. Existing direct-ingress
router examples are superseded, not prerequisites to the tunnel. Do not add a
second public path while validating the tunnel.

Cloudflare terminates client HTTPS; the connector link is encrypted, while its
Caddy hop is HTTP on a private Docker bridge. Caddy forwards the HTTPS scheme
and real client IP through an explicitly trusted connector peer. Secure the
separate Caddy-to-backend hop according to that network's trust boundary.

## Private Forgejo HTTPS remains separate

The existing `compose/caddy` and `11-caddy.yml` files describe a Forgejo proxy
candidate. They are not the public tunnel target. Do not publish that service
in Cloudflare or add a Forgejo route to the public Caddy configuration.

Forgejo currently uses its private application port during migration. A future
private HTTPS endpoint can use INNER's private DNS and either DNS-01 with a
scoped provider credential/module, or a private CA trusted by clients. The
existing public-ACME Caddyfile does not implement DNS-01 automatically. A private
DNS answer alone does not restrict network access or virtual-host routing.

Do not change Forgejo's root URL, bind address, SSH port or migration lifecycle
as part of tunnel deployment. Follow the [migration runbook](gitea-to-forgejo.md)
for those changes. Neither router administration nor Kubernetes, Docker, caches,
metrics, databases or queue endpoints belong in public tunnel routes.

## Verify and withdraw

Test the chat hostname over LAN and cellular, HTTP→HTTPS redirect, certificate,
authenticated messaging/upload/email and actual client IP. Probe unknown and
private Git hostnames through the public tunnel; they must not reach a backend.
Use the tunnel readiness probe as a connectivity signal, not app acceptance.

Keep real credentials, route inventories, account/tunnel identifiers and runtime
diagnostics out of commits, issue comments and CI artifacts. The detailed
runbook covers protected token rotation, credential backup and sanitized evidence.

To withdraw public ingress, stop `caddy-public.service` and remove/disable the
published application in Cloudflare. Private Forgejo and its state remain
independent. Retain token/configuration backups securely; do not delete
application state to disable external access.
