# Controller Zulip and public ingress

Deployed on the controller: Zulip, PostgreSQL, RabbitMQ, Redis, Memcached, Caddy and
cloudflared run in separate containers on the GitOps controller. No new VM or
router application installation is required. On 2026-11-18 the operator confirmed
healthy app/connector containers, public HTTPS, organization creation and owner
login. Remaining checks are recorded in the
[operator acceptance table](zulip-controller.md#accepted-and-pending-checks).

| Component | Responsibility |
| --- | --- |
| Cloudflare | Public chat DNS and browser-facing HTTPS |
| Controller cloudflared | Outbound-only tunnel connector |
| Controller Caddy | Exact-host routing on an unpublished listener |
| Controller Zulip | Application plus its own database, queue and caches |
| OUTER/INNER | Existing routing/firewall, WireGuard, DNS and unrelated DDNS |
| Forgejo | Existing private LAN/WireGuard service and separate state |

Use [Cloudflare Tunnel in Docker](cloudflared.md) for token and DNS setup, and
[Zulip on the controller](zulip-controller.md) for application configuration,
credentials, initialization and acceptance.

`compose/zulip/compose.yaml` is an overlay for
`compose/caddy-public/compose.yaml`. The installed `zulip-compose` helper always
uses both files and the single local `compose/caddy-public/.env`. The guarded
`caddy-public.service` owns the combined seven-container project. Stopping or
restarting this unit also stops or restarts Zulip; token rotation is a short
application maintenance operation in this profile.

The tunnel and Caddy share only their internal tunnel bridge. Caddy and Zulip
share a different internal bridge with fixed peer addresses; Zulip trusts only
Caddy's address there. Only Zulip and its four dependencies join the dependency
bridge; ingress containers stay off it. The
connector and application have separate outbound networks. No service in this
project publishes a host port, uses the Docker socket, joins Forgejo's network,
or uses Forgejo's database/Redis. Unknown public hostnames return 404.

The earlier separate-host bundle and `zulip-upstream.override.yaml` are inactive
compatibility material, not controller deployment entry points. This guide uses
the controller overlay; do not combine that bundle or its Caddy with this project.
Application HTTP stays inside Docker;
no controller-to-remote-backend firewall rule or public web DNAT is required.

For additional public services, add an explicit hostname route and a reviewed
backend connection. A public DNS record alone does not create a Caddy route.
The separate private `compose/caddy` Forgejo candidate must never become a
Cloudflare published application target.

## Acceptance boundary

The recorded controller has 4 GB RAM; cohosting is intended for a small group.
Threaded queue workers and per-container memory limits reduce its footprint.
Startup checks require memory/swap headroom and 10 GiB free SD state storage;
these checks do not prove that the current management workload and Zulip will
fit under sustained load. Monitor memory, swap and SD latency during acceptance.

Startup, tunnel readiness and browser login have passed. SMTP authentication also
passed from the host; invitation delivery is still unverified. Complete messaging,
uploads, cellular/native clients, real client-IP and private Forgejo checks, then
an off-device backup and isolated restore.
Record sanitized pass/fail summaries; keep settings, logs and credentials local.
