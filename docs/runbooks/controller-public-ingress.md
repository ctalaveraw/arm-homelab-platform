# Shared public Caddy on the GitOps controller

Decision: run the shared public Caddy instance on `gitops-controller-01`.
No new VM or router application installation is required. This profile is a
deployment candidate; public hostname, upstream host, DNS and live router rules
still need to be supplied and accepted.

| System | Responsibility |
| --- | --- |
| OUTER | Existing WAN firewall/WireGuard; forward TCP 80/443 inward |
| INNER | Existing routing/firewall, Cloudflare DDNS and local DNS |
| `gitops-controller-01` | Shared public Caddy; initially Zulip hostname only |
| Zulip application host | Compose application/database stack; location still pending |
| Forgejo | Private LAN/WireGuard access on its migration/final application port |

The controller's last supplied LAN address was `10.0.0.50`. Verify it before
using it. INNER's disabled draft redirects now target the controller, not a
Zulip VM. The existing transit-DNAT candidate remains conditional on the actual
route/NAT inventory; no live network change is made by this document.

## Public and private routing

Use `compose/caddy-public/compose.yaml` for public ingress. It has one exact
public hostname, no wildcard/catch-all, no Forgejo route, no Docker socket and
no membership in Forgejo's `platform_ingress` network. Its certificate state is
separate and guarded on the SD filesystem. Systemd owns startup.

The existing `compose/caddy` / `11-caddy.yml` profile routes to Forgejo. Do not
use that profile as the public listener or run it on the same address/ports as
this profile. Merely omitting a public Git DNS record does not make a routable
Forgejo virtual host private: external clients can supply its hostname.

This stage leaves Forgejo on its existing private HTTP port while migration
continues. Private Forgejo HTTPS is a separate listener/policy decision; adding
its hostname to public Caddy would violate the selected access boundary. Once
WAN forwarding is active, never replace the public profile with the legacy
Forgejo profile on the forwarded listener. Disable the WAN redirects first if
changing listener ownership. The new playbook and storage guard reject an
active legacy `caddy.service`; they do not modify or stop it automatically.

All new source paths are additive. No migration runbook, Forgejo manifest,
existing Caddy profile, root README or shared CI script is edited by this change.

## Configure the controller

Confirm SD storage, actual LAN address, free TCP 80/443 and nonoverlapping Docker
routes. Verify `/usr/bin/docker-compose` is the modern Compose CLI used by this
host. The manifest uses an independent Docker bridge, not host networking.

```bash
cd /srv/platform
ss -lntup
ip -4 route show table all
docker network ls
cp -n compose/caddy-public/.env.example compose/caddy-public/.env
chmod 600 compose/caddy-public/.env
```

Set `PROXY_BIND_IP` to the controller LAN address, `ZULIP_FQDN` to the chosen
public hostname, `ACME_EMAIL` to your contact and `ZULIP_UPSTREAM` to the actual
restricted application endpoint. Never use the public chat URL as its own
upstream. Add more public hostname blocks deliberately when another service is
approved; additional hosts share these same public web ports.

After backend preparation, hostname/DNS selection and router review, deploy:

```bash
ansible-playbook ansible/playbooks/caddy-public.yml --ask-become-pass
```

The unit validates Caddy before starting. Automatic public certificate issuance
requires the chosen hostname and reachable ACME validation path; config
validation alone does not prove it. Router redirects remain disabled until the
public-only configuration and its listener ownership are confirmed.

## Adapt the earlier Zulip source bundle

The original `homelab-zulip-v0.1.0.zip` colocated Caddy with the application.
That placement is superseded. A new VM is not required for the application;
choose an existing machine with sufficient RAM/storage and review isolation.

For a separate application host, copy `zulip-upstream.override.yaml` from this
directory next to that bundle's `compose.yaml`. Keep the bundle's `.env` and add
`CONTROLLER_PROXY_IPV4` with the exact proxy source observed at the application
(normally the controller LAN address for a remote backend). All application
lifecycle commands must use both manifests:

```bash
docker compose -f compose.yaml -f zulip-upstream.override.yaml config --quiet
docker compose -f compose.yaml -f zulip-upstream.override.yaml run --rm zulip app:init
docker compose -f compose.yaml -f zulip-upstream.override.yaml up -d --wait zulip
```

The override profiles the bundle's local Caddy out of default startup, publishes
only Zulip HTTP on the selected backend IPv4/TCP 8080, and trusts the controller
instead of the bundle's old Caddy container IP. Do not explicitly start the
`legacy-collocated-ingress` profile. If it was previously started, remove that
old Caddy container before switching; changing profiles does not remove existing
containers. Do not execute the bundle's old unqualified Caddy/backup instructions
without adapting them to the two-host layout and both manifests.

Only the controller may connect to backend TCP 8080. Use a routed services zone
plus the explicit INNER rule, or enforce this in the backend host's container
forwarding firewall if the machines share L2. Router rules cannot filter traffic
that never crosses the router. An IPv4 bind alone is not source filtering.
Use verified upstream HTTPS if the path crosses an untrusted network. Verify
real client IPs and HTTPS links; never trust all private addresses or the entire
Docker gateway range. Caddy and app container DNS aliases do not cross hosts.

If Zulip is also placed on the controller, review memory/storage headroom and
use a dedicated shared Docker backend network instead of exposing a host HTTP
port. That cohosted profile is not supplied here; the application location has
not been selected. Do not guess which proxy source the app will see.

## DNS and acceptance

Cloudflare: initially use a DNS-only chat record through the existing IPv4 DDNS
name. INNER's exact chat hostname override points to the controller, not the
application host. LAN/WireGuard clients use the same controller HTTPS endpoint.
Keep Forgejo's private DNS/service endpoint independent. Publish no AAAA route
until IPv6 ingress policy has been reviewed. TCP 443 leaves WireGuard UDP 443
unchanged; HTTP/3 is disabled in this profile.

Before inviting users, verify LAN and cellular HTTPS, hostname-matching trusted
certificate, login/messages/uploads/email, actual client IP, restricted backend
reachability, continued private Forgejo access and failed WAN access to Forgejo.
Test the private Git hostname explicitly from outside with a forced Host/SNI
mapping to the public IP; absence of public DNS is not a privacy test.

Back up `services/caddy-public/data`, its configuration and the application
state separately. Disabling OUTER's two public redirects closes public ingress
without stopping Forgejo or deleting Caddy/application state.
