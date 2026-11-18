# Cloudflare Tunnel in Docker

Status: repository configuration prepared; real account setup and live acceptance
are pending. No token, real hostname, tunnel/account identifier, backend address,
local network inventory or runtime diagnostic output belongs in this repository.

The controller's `caddy-public` Compose project contains two containers:

| Component | Responsibility |
| --- | --- |
| Cloudflare edge | Public DNS and browser-facing HTTPS |
| `cloudflared:2026.11.1` | Outbound-only, remotely managed connector; image pinned by multi-arch digest |
| Caddy | Internal HTTP listener and exact-host reverse proxy |
| Application host | Zulip and its database/cache/queue stack |

Traffic is Cloudflare → cloudflared → Caddy → Zulip. The two containers share a
private Docker network with fixed, locally selected peer addresses. They have
separate outbound networks so Docker DNS selects that shared private path.
Neither container publishes host ports or joins Forgejo's network. No inbound
TCP 80/443 forwarding or Caddy ACME/DNS-01 credential is required for this path.

Cloudflare terminates browser HTTPS, and its connector transport is encrypted.
HTTP between the two controller containers stays on their private Docker bridge.
Restrict Caddy-to-application HTTP to a protected network; use verified upstream
TLS if that connection crosses an untrusted network. The tunnel does not create
an independently encrypted Caddy-to-application connection.

## 1. Prepare local configuration

Copy `compose/caddy-public/.env.example` to `.env` in that directory and set mode
0600. Fill the exact chat hostname and restricted upstream endpoint locally.
Choose a Docker subnet that does not overlap host, LAN, VPN or existing Docker
routes. Set Caddy and cloudflared to different usable addresses in that subnet;
exclude the subnet's network, broadcast and first/gateway addresses. Use the same
cloudflared address for Caddy's peer trust. No deployment values are committed.

Do not put a tunnel token in `.env`, a Compose command, a shell variable, a
command-line argument, a PR, a screenshot or chat. This deployment uses a file
secret; the Cloudflare account API key and account-wide certificate are not
needed by either container.

## 2. Prepare the host without starting the tunnel

From the controller checkout with its existing Ansible environment:

```bash
ansible-playbook ansible/playbooks/caddy-public.yml --ask-become-pass
```

The default run creates guarded SD directories, installs the hidden-input token
helper and lifecycle unit, and reloads systemd. It does not enable/start a new
tunnel. It also does not stop an already running service; plan a restart when
changing an existing deployment.

## 3. Create a remotely managed tunnel and install its token

In your Cloudflare account, create a remotely managed Cloudflare Tunnel for this
connector. Use its named-tunnel token; a Quick Tunnel is not this deployment.
Copy the token from the dashboard's connector installation instructions without
running or saving its token-bearing Docker command.

On the controller, run:

```bash
sudo /usr/local/sbin/cloudflared-install-token
```

Paste into the hidden prompt. The helper verifies the expected SD filesystem,
refuses accidental replacement, writes atomically and never prints the value.
The credential file is `/srv/storage/state/services/cloudflared/tunnel-token`,
owned by root with numeric group 65532 and mode 0440. Its parent is root-owned
0700. The official container runs as 65532:65532 and receives only that file at
`/run/secrets/tunnel_token`.

Local Compose secrets are bind-mounted files, not encrypted Swarm secrets.
Their source ownership/mode must allow the nonroot container to read them;
Compose's uid/gid/mode overrides are not relied on. Back up this private file
securely off-device. Never copy it under the source checkout.

If moving an existing native connector, preserve unrelated tunnels and services.
Replicas of one remotely managed tunnel share its origin configuration; the
Docker-only `server:8080` origin will not resolve on an older native connector.
Use a dedicated chat tunnel or coordinate that cutover after testing every
remaining replica. Do not stop an existing router connector blindly.

## 4. Publish only the selected chat hostname

Configure the tunnel's published application hostname in Cloudflare with:

| Field | Value |
| --- | --- |
| Public hostname | Your chosen chat name, kept in local `.env` |
| Service type | HTTP |
| Service URL | `server:8080` (`http://server:8080`) |
| Path | All paths for this hostname |

The hostname must match `ZULIP_FQDN`. Preserve the public Host header; if an
origin Host override is needed, set it to that same hostname in Cloudflare.
Keep Forgejo, controller administration, metrics, Docker and database endpoints
out of the tunnel's published applications. Caddy also returns 404 for unknown
hostnames, so publishing a second hostname does not automatically expose a
backend. Each additional public service needs a reviewed Caddy route.

Use Cloudflare's tunnel-managed DNS record for chat, not a DNS-only A/CNAME to
residential DDNS. Remove only a conflicting chat record when replacing it.
Keep existing DDNS for WireGuard and unrelated services. No public IP, tunnel
UUID or account/zone ID needs to be recorded in Git.

LAN/WireGuard clients initially use the same public Cloudflare answer. Remove
only an old chat-specific local override if one was previously applied; pointing
chat directly at the controller will not work with this unpublished internal
listener. Do not remove private Forgejo DNS or globally disable DNS rebind
protection. A separate direct private chat endpoint is not supplied by this
profile.

## 5. Allow egress and activate

The controller needs DNS and outbound Cloudflare Tunnel connectivity on TCP/UDP
7844; cloudflared chooses QUIC or HTTP/2. Review the provider's current endpoint
requirements if egress is restricted. Add no broad inbound allowance on OUTER
or INNER. Keep the old direct-web DNAT examples disabled; this path replaces
their role. Existing WireGuard ingress and its DDNS remain independent.

After reviewing the tunnel's published hostname, local configuration, original
Zulip backend and token file:

```bash
ansible-playbook ansible/playbooks/caddy-public.yml --ask-become-pass \
  -e public_ingress_activate=true
```

Systemd validates SD state, token permissions, peer addresses and the rendered
Compose contract. It validates Caddy, starts both containers and waits for the
connector's `/ready` health check. A failed start removes partial containers;
application state and the secret remain on disk. This is the only activation
profile for this tunnel; do not start a second manual Docker connector with a
token in its arguments.

## Verification and proxy headers

Use `systemctl status caddy-public` and the project's `docker-compose ps` first.
The connector's readiness probe uses its own loopback metrics endpoint; neither
metrics nor Caddy's administration interface is published. Readiness proves a
tunnel connection, not successful Zulip initialization or authentication.

Verify actual HTTPS from LAN and cellular, HTTP→HTTPS redirect, login, messaging,
long polling, upload, email and the correct public URLs. Zulip must trust the
exact Caddy source it observes, not cloudflared, all private networks or arbitrary
X-Forwarded-For values. Caddy trusts only cloudflared's fixed peer address,
uses Cloudflare's CF-Connecting-IP header, and sends an HTTPS scheme upstream.
The smoke test checks spoofed X-Forwarded-For, redirects and wrong peer/hostname
rejection with synthetic loopback requests.

Test that neither the private Git hostname nor other controller services can
be reached through this tunnel. No public DNS record alone is a privacy control.
Keep Zulip invitation-only and test native clients before putting an additional
interactive Cloudflare Access login in front of its API.

## Rotation, restart, backup and rollback

Rotate the token in Cloudflare first, then install the replacement:

```bash
sudo /usr/local/sbin/cloudflared-install-token --replace
sudo systemctl restart caddy-public
```

Recreating the container is required after an atomic secret replacement because
an existing bind mount can retain the old inode. Do not reset unrelated Cloudflare
API keys or copy in account-wide certificates. Update the image tag deliberately
through Git; autoupdate is disabled.

Back up the local `.env`, public Caddy configuration and token privately, along
with application data. Runtime logs and diagnostic bundles can contain real
routes, IDs, addresses and request metadata even though the token is file-based.
Warning-level logging and disabled management diagnostics reduce output; do not
commit or paste unreviewed logs, `docker inspect` or rendered real configuration.
Use sanitized summaries when recording deployment evidence.

Stopping `caddy-public.service` removes both containers and their networks while
preserving SD state and Forgejo. Remove/disable the published application in
Cloudflare if withdrawing the service. No router port-forward rollback is needed
for this tunnel path. Systemd's guarded oneshot lifecycle does not automatically
restart a crashed container; monitor readiness and restart through the unit.

## Source references

- [Cloudflare run parameters and token-file support](https://developers.cloudflare.com/tunnel/reference/run-parameters/)
- [Cloudflare tunnel tokens](https://developers.cloudflare.com/tunnel/reference/tunnel-tokens/)
- [Cloudflare Docker deployment](https://developers.cloudflare.com/tunnel/get-started/)
- [Cloudflare tunnel firewall requirements](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/tunnel-with-firewall/)
- [Cloudflare HTTP header semantics](https://developers.cloudflare.com/fundamentals/reference/http-headers/)
- [Caddy trusted proxy settings](https://caddyserver.com/docs/caddyfile/options#trusted-proxies)
