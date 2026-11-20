# Zulip on the GitOps controller

Status: deployed on the controller. The operator confirmed public HTTPS,
organization creation and owner login on 2026-11-18. This profile uses the official
Zulip 13.2-0 image and PostgreSQL 14 dependency image with state separate from
Forgejo. Source and lifecycle names are mapped in the
[deployment standards](../architecture/deployment-standards.md).

## Accepted and pending checks

These are operator-reported results, not a new remote inspection of the host.
Keep deployment addresses, account identifiers, credentials, creation links and
screenshots outside the public repository.

| Check | Recorded result on 2026-11-18 |
| --- | --- |
| Preparation | Repeat Ansible run: `ok=14 changed=0 failed=0` |
| Initialization | Database migrations completed; `=== End Initial Configuration Phase ===` |
| Combined lifecycle | `Result=success`, `ActiveState=active`, `SubState=exited`; all seven containers running |
| Application and connector | Zulip and cloudflared both reported healthy |
| Public access | Exact hostname corrected; public DNS, HTTPS, organization creation and owner login confirmed |
| SMTP submission | Gmail connection, verified TLS and authentication passed from the controller; message delivery not yet confirmed |
| Organization policy | Invitation-only setting still needs explicit verification in Organization permissions |
| Functional acceptance | Invitation email, user-posted messages, uploads, real-time updates and cellular/native-client access pending |
| Capacity and isolation | Sustained resource use, actual client-IP forwarding, private-service negative tests and post-deployment Forgejo checks pending |
| Recovery | First protected checkpoint, off-device copy, isolated restore and full-host reboot test pending |

The last supplied container inventory showed Prometheus and Grafana stopped.
Earlier telemetry acceptance does not establish current monitoring or memory
headroom for this combined workload. Restore monitoring only after a capacity
review; this runbook does not start unrelated services.

## Routine operations

Run these commands on the controller. The installed `zulip-compose` helper
selects both manifests and the single private `.env`. `caddy-public.service`
owns Caddy, cloudflared, Zulip and all four dependencies; there is no independent
Zulip systemd unit.

| Operation | Command | Effect |
| --- | --- | --- |
| Unit state | `sudo systemctl show caddy-public.service -p ActiveState -p SubState -p Result` | Read-only lifecycle result |
| Container state | `sudo /usr/local/sbin/zulip-compose ps --all` | Read-only component and health status |
| Follow startup | `sudo journalctl -u caddy-public.service -n 40 -f --no-pager -o cat` | Read-only live progress |
| Check inputs | `sudo /usr/local/sbin/caddy-public-check-storage` | Storage, credentials, isolation and cold-start capacity checks |
| Start / stop | `sudo systemctl start caddy-public` / `sudo systemctl stop caddy-public` | Start or remove the combined containers; preserve SD state |
| Apply reviewed configuration | `sudo systemctl restart caddy-public` | Restart the entire seven-container stack through the guard |

`active/exited` is normal for this oneshot unit. It does not mean containers
exited, and it does not continuously prove application health. The `PORTS` column
may show image-exposed ports without a host mapping; this profile publishes none.

Restart waits for readiness for up to 900 seconds inside a 1200-second unit
startup timeout. It can remain quiet in the calling terminal. Use a second
terminal to follow the journal and inspect `ps --all`; a command chained with
`&&` runs only after restart succeeds. If a terminal wait is interrupted, inspect
the current job and container state before issuing another restart.

## Diagnose startup and routing

Use the unit result, `ps --all` and recent journal lines together. A failed unit
start cleans up partial containers, so an empty container listing can follow a
real startup failure. Application state remains on SD.

| Symptom | Check and repair |
| --- | --- |
| Compose interpolation fails | Run `sudo /usr/local/sbin/zulip-compose config --quiet`; add missing keys from `.env.example` without replacing the existing file |
| Token empty or not single-line | Re-enter only the connector token using `cloudflared-install-token --replace`, then restart the unit; retain unrelated Cloudflare credentials |
| Source secret permission failure | Preserve all values; check root ownership, source directory 0700 and six regular files 0444; token metadata is different |
| `Error accessing Zulip secrets` during init | Repair only the `/zulip/data` mount directory to root-owned 0755; details below |
| Caddyfile permission denied | Repair only the checkout's public Caddyfile to 0644; details below |
| Public resolver returns NXDOMAIN | Compare the entire hostname and zone with the published application, its DNS record and local `ZULIP_FQDN` |
| Public DNS resolves but the client cannot | Check the client's resolver, negative cache and chat-specific local overrides; retain private Forgejo DNS and global rebind protection |
| HTTP 404 | Check the exact hostname, tunnel route and full setup path; unknown Caddy hostnames deliberately return 404 |
| HTTP 502 | Check tunnel Service URL `http://server:8080`, Caddy upstream and Zulip health; use targeted logs privately |
| Mail auth passes but email is absent | Send an actual invitation, check recipient spam and inspect the application/queue result; authentication alone is not delivery |

For a hostname check, print only the needed setting locally:

```bash
sudo grep '^ZULIP_FQDN=' /srv/platform/compose/caddy-public/.env
```

On the affected client, compare its resolver with a public resolver. Replace the
example with that exact hostname:

```bash
nslookup chat.example.com
nslookup chat.example.com 1.1.1.1
```

Cloudflare's Subdomain plus Domain, its DNS record, the published application
hostname and `ZULIP_FQDN` must agree. After correcting the local value, restart
the unit so Caddy and Zulip both receive it. Before an organization exists,
generate a new creation link and open its full path privately. Do not change a
working organization's domain casually; that is a separate application migration.

For multiple organizations, `ZULIP_FQDN` remains the server base. Add exact
organization addresses through `ZULIP_ORG_HOSTS` and matching tunnel routes;
follow the [organization migration runbook](zulip-organizations.md) before
renaming an existing organization. Each organization request must retain its
own Host header through the proxy.

Use targeted `zulip-compose logs --tail 50 server zulip cloudflared` only for
local diagnosis. Review and redact results before sharing. Full `.env`, rendered
production configuration, `docker inspect` and SMTP debug transcripts can expose
deployment details or credentials.

## Prepare an installation

Update the controller checkout without overwriting local work, then run the
existing preparation playbook in its Ansible environment:

```bash
cd /srv/platform
ansible-playbook ansible/playbooks/caddy-public.yml --ask-become-pass
```

This installs `zulip-compose`, `zulip-init-secrets`, the storage guard and the
combined lifecycle unit. It preserves ownership of database, queue and Redis
directories already initialized by their images. The application data mount
is root-owned mode 0755 so the container's `zulip` user can read its generated
configuration. Its host parent remains root-owned mode 0700. Preparation also
corrects an existing application data mount created with mode 0700, without
changing the contents or ownership of files below it. The default run does not
start containers.

Preparation sets the checkout's public `Caddyfile` to mode 0644 and preserves its
owner. Caddy drops all capabilities, so a mode 0600 file owned by the checkout
user is unreadable inside the container even when Caddy runs as root. This file
contains the proxy template; credentials remain in their separate protected files.

Keep `compose/caddy-public/.env` mode 0600. If it already exists, add missing
keys from `.env.example`; do not replace it. Configure these values locally:

| Setting | Meaning |
| --- | --- |
| `ZULIP_FQDN` | Exact public chat hostname; no scheme, port or path |
| `ZULIP_UPSTREAM` | `http://zulip:80`; the overlay also enforces this value |
| `PUBLIC_INGRESS_SUBNET` | Unused Docker IPv4 subnet for tunnel/Caddy |
| `CADDY_TUNNEL_IP`, `CLOUDFLARED_CONTAINER_IP` | Distinct usable peers on that subnet |
| `ZULIP_PROXY_SUBNET` | A second unused subnet, distinct from tunnel/LAN/VPN networks |
| `CADDY_ZULIP_IP`, `ZULIP_CONTAINER_IP` | Distinct usable peers on the application proxy subnet |
| `ZULIP_ADMIN_EMAIL` | Server administrator contact |
| `SMTP_HOST`, `SMTP_USER`, `SMTP_FROM` | Outgoing SMTP submission provider and sender |

Exclude each subnet's network, broadcast and first/gateway addresses. The two
Caddy addresses serve different bridges and are not the controller's LAN IP.
SMTP uses STARTTLS on port 587. Configure a valid provider account and sender;
the SMTP password is entered separately and never goes in `.env`.

For Gmail, use `SMTP_HOST=smtp.gmail.com`; set the user and sender to the chosen
account locally. Enable Google 2-Step Verification and create an app password.
Enter its 16 characters without the display-grouping spaces. The ordinary account
password is not the app password. Availability depends on the account's Google
policy; see [Google's app-password instructions](https://support.google.com/accounts/answer/185833).

Install the Cloudflare token using the [tunnel guide](cloudflared.md), then:

```bash
sudo /usr/local/sbin/zulip-init-secrets
```

Enter the SMTP submission password in the hidden prompt. The helper creates
five random application/service secrets and the email password together under
`/srv/storage/state/services/zulip/secrets`. It refuses to overwrite an existing
set. Do not regenerate credentials to repair a partial or existing deployment;
restore the original set from a private backup instead.

File secrets are root-owned mode 0444 inside a root-owned 0700 source directory,
so nonroot container services can read their bind-mounted file without exposing
the source directory to ordinary host users. Local Compose secrets are not an
encrypted credential store. Protect an off-device backup of these files.

For an existing installation, repair or replace only the affected credential.
For example, edit the SMTP password with `sudoedit` on
`/srv/storage/state/services/zulip/secrets/email_password`, preserve root ownership
and mode 0444, then restart the unit. Keep the other five values unchanged.
The initial secret installer intentionally refuses to replace an existing set.

## Initialize and activate

The guard checks the real `storage_sdcard` ext4 mount, canonical bind sources,
secret permissions, proxy trust and network isolation. A cold start also needs
at least 3 GiB total host RAM, 1 GiB configured swap, 1.5 GiB available RAM and
10 GiB free on SD state storage. These are minimum startup checks, not a workload
capacity guarantee. Docker image layers use the controller's eMMC data root;
check its available space before pulling. Existing zram is not off-device storage.
No swap, storage or unrelated workload changes happen automatically.

```bash
sudo /usr/local/sbin/caddy-public-check-storage
sudo /usr/local/sbin/zulip-compose pull
sudo /usr/local/sbin/zulip-compose run --rm zulip app:init
```

The last command should finish with `=== End Initial Configuration Phase ===`.
Dependencies started by this initialization command remain running. If init
fails, preserve state and diagnose locally; use `zulip-compose down` to stop
partial containers. Do not delete the database or secrets and retry.

If an earlier preparation run created the application data directory as
root-owned mode 0700, initialization can report `Error accessing Zulip secrets`
even though the image already runs its validation command as `zulip`. The
generated `/etc/zulip/zulip-secrets.conf` links through `/data`, which that user
must be able to traverse. Rerun the updated preparation playbook, or repair
only the mount directory and retry:

```bash
sudo chmod 0755 /srv/storage/state/services/zulip/data
sudo /usr/local/sbin/zulip-compose run --rm zulip app:init
```

This preserves the source credentials and generated configuration. The source
credential directory remains mode 0700 and its six files remain mode 0444.

Configure only the chat published application with the full Service URL
`http://server:8080` in Cloudflare (including `http://`). Choose the intended chat
subdomain and leave Path empty. Use its tunnel-managed DNS; add no router inbound web forwards or
chat-to-controller local DNS override. Then activate explicitly:

```bash
ansible-playbook ansible/playbooks/caddy-public.yml --ask-become-pass \
  -e public_ingress_activate=true
sudo /usr/local/sbin/zulip-compose ps
```

If Caddy validation reports permission denied opening `/etc/caddy/Caddyfile`,
rerun the updated preparation playbook or repair the one bind source and restart:

```bash
sudo chmod 0644 /srv/platform/compose/caddy-public/Caddyfile
sudo systemctl restart caddy-public
sudo /usr/local/sbin/zulip-compose ps
```

Startup waits for the official application's `/health` probe and the tunnel's
readiness probe. A failed unit start cleans up partial containers and preserves
SD data. Initialization on ARM may take several minutes. The service is a
storage-guarded oneshot; container restart policies remain disabled. Monitor
health and restart through systemd so storage checks run again.

Generate the initial organization creation link locally:

```bash
sudo /usr/local/sbin/zulip-compose exec --user zulip \
  --workdir /home/zulip/deployments/current zulip \
  ./manage.py generate_realm_creation_link
```

The creation link is sensitive; open it yourself, not in a public issue or chat.
Create the organization and select invitation-only signup. Open organization
creation is disabled at the server level. Verify login, an invitation email,
messages, real-time updates, uploads and native clients from LAN and cellular.
Confirm real client IPs, bounded memory/swap behavior, and unchanged private
Forgejo access. No database/cache/queue/SMTP-listener host port is published.

## Reviewed changes and upgrades

Use `zulip-compose` for all manual operations so both manifests are always
included. Use `systemctl restart caddy-public` for reviewed configuration or
image updates; `state: started` in Ansible does not recreate a running stack.
This restarts Zulip, Caddy and cloudflared together. Updating the tunnel token
also requires that restart to replace the secret bind mount.

Review local work with `git status --short`, fetch the canonical `github` remote,
and update with a fast-forward-only merge. Do not reset or clean a shared checkout.
Run the preparation playbook to install changed guards/helpers/units before
restarting; a pull alone does not update installed copies. Review upstream upgrade
and database compatibility before changing image references. Preserve the stable
RabbitMQ hostname and existing state/credentials across container recreation.

The current image set includes moving series/distribution tags. `pull` can change
those dependencies even when their manifest text is unchanged; treat it as an
image update in a maintenance window. Capture image identities privately before
the change. Source and image rollback alone cannot reverse a database migration.

## Backup and recovery

The following procedure is ready for operator use; successful backup and restore
have not yet been reported. Before an upgrade, refresh the logical database dump:

```bash
sudo /usr/local/sbin/zulip-compose exec -T zulip /sbin/entrypoint.sh app:backup
```

Require exit status zero and `Backup process succeeded.` Check that the resulting
`backup-*.sql` file is nonempty and readable by `pg_restore --list`; the upstream
image writes a PostgreSQL custom-format dump despite the `.sql` extension.

| Protected checkpoint material | Why it is required |
| --- | --- |
| `/srv/storage/state/services/zulip/data` | Fresh dump, uploads and generated application configuration/secrets |
| `/srv/storage/state/services/zulip/secrets` | Original six file credentials used by this Compose deployment |
| `/srv/platform/compose/caddy-public/.env` | Exact hostname, SMTP account, subnet and peer settings |
| Public Caddyfile and `/srv/storage/state/services/caddy-public` | Proxy source and persistent Caddy state |
| `/srv/storage/state/services/cloudflared/tunnel-token` | Connector credential; protect as a secret |
| Source revision, image identities and private Cloudflare route/DNS record | Reconstruct the matching software and external routing configuration |

For a filesystem checkpoint:

1. Complete the fresh dump, then stop `caddy-public.service` for a consistent
   application/filesystem copy. This is a chat maintenance window; Forgejo remains
   separate.
2. Copy the listed material to a private checkpoint directory outside the checkout,
   such as a root-owned 0700 directory under `/srv/backups`. Preserve numeric
   ownership, modes and any ACLs. Copy uploads and credentials as well as SQL.
3. Restart through systemd and verify both container health and an authenticated
   application operation. If checkpoint creation failed, record that failure
   before resuming service; do not label an incomplete copy a backup.
4. Encrypt and transfer the checkpoint to an independent destination. Verify its
   checksum and retrieval from that destination. Keep the recovery key accessible
   without this controller, Forgejo or the tunnel.
5. Restore on an isolated target and verify accounts, messages, uploads and
   credentials before recording recovery acceptance. The hard-coded project and
   helper paths make the live controller unsuitable for a parallel restore test.

The image defaults to daily local database dumps unless overridden. That schedule
and its results still need checking on this host. A same-SD dump or same-controller
checkpoint does not provide off-device recovery. Scheduled encrypted backup,
retention and restore are tracked separately from successful startup.

The [version-matched upstream backup guide](https://github.com/zulip/docker-zulip/blob/13.2-0/docs/how-to/compose-backups.md)
uses named volumes; this profile uses guarded bind mounts. Restore the protected
files and their metadata on the isolated target, then use the upstream
`app:restore` procedure with the intended dump and matching application/database
versions. Do not copy named-volume deletion examples into production or use a
restore as a connectivity test. Keep the original checkpoint until the isolated
restore is accepted.

## Closeout when the operator is available

Confirm invitation-only signup in Organization permissions. Send an email
invitation to a second controlled address and verify delivery, then test a message,
small upload and real-time updates across two sessions. Use a cellular client and
the native client as separate checks. Check HTTP-to-HTTPS redirect, real client
IP forwarding, unknown/private-host rejection and continued private Forgejo access.

Record bounded memory/swap and SD behavior under the combined workload, then the
checkpoint/off-device/restore and reboot results above. Update the acceptance
table and [OPS-020](../planning/objectives.md#ops--out-of-cluster-host-operations)
only with the tests actually performed. Documentation and portable validation
can be completed independently; they do not close these site checks.

## Sources

- [Official Docker deployment](https://zulip.readthedocs.io/projects/docker/en/latest/)
- [Getting started](https://zulip.readthedocs.io/projects/docker/en/latest/how-to/compose-getting-started.html)
- [Proxy trust](https://zulip.readthedocs.io/projects/docker/en/latest/how-to/compose-ssl.html)
- [Threaded workers and environment](https://zulip.readthedocs.io/projects/docker/en/latest/reference/environment-vars.html)
- [Hardware requirements](https://zulip.readthedocs.io/en/13.2/production/requirements.html)
- [Backup model](https://zulip.readthedocs.io/projects/docker/en/latest/how-to/compose-backups.html)
