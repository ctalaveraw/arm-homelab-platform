# Shared public ingress on the controller

Selected deployment: Dockerized cloudflared and Caddy on the GitOps controller.
No new VM or router application installation is required. Deployment and live
acceptance remain pending; configuration examples contain no local deployment
addresses, real domains, tunnel identifiers or credentials.

Follow [Cloudflare Tunnel in Docker](cloudflared.md) for preparation, protected
token installation, Cloudflare published-hostname setup, activation and rollback.

| Component | Responsibility |
| --- | --- |
| OUTER/INNER | Existing firewall/routing, WireGuard, DNS and DDNS |
| cloudflared | Outbound-only connector to Cloudflare |
| Caddy | Internal exact-host routing; no published host web ports |
| Zulip host | Application/database stack; placement still pending |
| Forgejo | Existing private LAN/WireGuard service |

This supersedes the earlier direct TCP 80/443 forwarding plan. Do not activate
its router DNAT rules or its chat-to-controller local DNS override for this
profile. Cloudflare's tunnel-managed DNS replaces residential DDNS for the chat
hostname; unrelated DDNS/WireGuard configuration stays in place.

Public Caddy has no Forgejo route, no Docker socket and no membership in Forgejo's
private Docker network. The existing `compose/caddy` private-ingress candidate
and public tunnel profile use separate networks and state. Because the tunnel
profile publishes no host ports, it can coexist with a separately reviewed
private listener without taking over that listener or exposing it through WAN.
Never publish the legacy Forgejo proxy as a Cloudflare application service.

## Application profile from the earlier bundle

The original Zulip source bundle colocated Caddy with the application. That
placement is superseded. For a separate existing application host, copy
`compose/caddy-public/zulip-upstream.override.yaml` next to the bundle's
`compose.yaml`. Keep real settings local. Add `CONTROLLER_PROXY_IPV4` for the
exact proxy source observed at Zulip, normally the controller's address for a
remote backend. Use both manifests for every application lifecycle operation:

```bash
docker compose -f compose.yaml -f zulip-upstream.override.yaml config --quiet
docker compose -f compose.yaml -f zulip-upstream.override.yaml run --rm zulip app:init
docker compose -f compose.yaml -f zulip-upstream.override.yaml up -d --wait zulip
```

The override excludes the bundle's old Caddy from default startup, publishes
only backend HTTP on the selected application IPv4/TCP 8080, and limits proxy
trust to the configured controller source. If the old Caddy container already
exists, stop/remove it before switching; changing profiles does not remove an
existing container. Adapt old backup commands to use both manifests and back
up the controller's tunnel configuration/secret separately.

Only the controller may reach backend TCP 8080. Enforce that in INNER for a
routed services segment or in the backend host's container-forwarding firewall
when both machines share L2. A private IPv4 bind alone is not a source allowlist.
Use verified upstream TLS for an untrusted path. For cohosting on the controller,
review RAM/storage and use an unpublished dedicated shared Docker backend network;
that application-placement profile is not assumed or implemented here.

## Acceptance boundary

Repository validation and synthetic proxy tests do not prove a connected real
tunnel, correct published hostname, working mail or app recovery. Accept the
service only after public/LAN HTTPS, client IP, login/messages/uploads/email,
backend source restrictions, private Forgejo access and backup/restore have
been verified. Record sanitized results, not local route/configuration dumps.
