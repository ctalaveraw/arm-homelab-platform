# Zulip on the GitOps controller

Status: controller placement selected; source validation and live acceptance are
separate. This profile uses the official Zulip 13.2-0 image and its PostgreSQL 14
dependency image, both published for ARM64. It creates a new installation with state separate from Forgejo.

## Prepare

Update the controller checkout without overwriting local work, then run the
existing preparation playbook in its Ansible environment:

```bash
cd /srv/platform
ansible-playbook ansible/playbooks/caddy-public.yml --ask-become-pass
```

This installs `zulip-compose`, `zulip-init-secrets`, the storage guard and the
combined lifecycle unit. It creates missing SD data directories without
reassigning ownership of directories already initialized by service images.
The default run does not start containers.

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

Configure only the chat published application with the full Service URL
`http://server:8080` in Cloudflare (including `http://`). Choose the intended chat
subdomain and leave Path empty. Use its tunnel-managed DNS; add no router inbound web forwards or
chat-to-controller local DNS override. Then activate explicitly:

```bash
ansible-playbook ansible/playbooks/caddy-public.yml --ask-become-pass \
  -e public_ingress_activate=true
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

## Operations and recovery

Use `zulip-compose` for all manual operations so both manifests are always
included. Use `systemctl restart caddy-public` for reviewed configuration or
image updates; `state: started` in Ansible does not recreate a running stack.
This restarts Zulip, Caddy and cloudflared together. Updating the tunnel token
also requires that restart to replace the secret bind mount.

Before upgrading, run a database backup:

```bash
sudo /usr/local/sbin/zulip-compose exec zulip /sbin/entrypoint.sh app:backup
```

This writes the database dump into the app's `/data/backups`. A complete private
backup also needs the rest of `/srv/storage/state/services/zulip/data`, the six
source secrets, local `.env` and the tunnel token/configuration. Stop the unit
before a filesystem copy for a consistent snapshot; raw PostgreSQL directory
copies while it is running are not a substitute for `app:backup`. Store backups
off-device with encryption/access controls and test restore in isolation before
claiming recovery. The built-in backup on the same SD card is not disaster recovery.

Restoring a database replaces data; follow the upstream restore procedure in a
separate, isolated rehearsal first. Do not run restores against a live controller
as a connectivity test. Stopping `caddy-public.service` removes all seven
containers while preserving SD state; Forgejo and router policy are independent.

## Sources

- [Official Docker deployment](https://zulip.readthedocs.io/projects/docker/en/latest/)
- [Getting started](https://zulip.readthedocs.io/projects/docker/en/latest/how-to/compose-getting-started.html)
- [Proxy trust](https://zulip.readthedocs.io/projects/docker/en/latest/how-to/compose-ssl.html)
- [Threaded workers and environment](https://zulip.readthedocs.io/projects/docker/en/latest/reference/environment-vars.html)
- [Hardware requirements](https://zulip.readthedocs.io/en/13.2/production/requirements.html)
- [Backup model](https://zulip.readthedocs.io/projects/docker/en/latest/how-to/compose-backups.html)
