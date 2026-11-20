# Move Zulip to separate organization hostnames

Status: source preparation. No controller migration or Cloudflare certificate
acceptance is recorded by this change. Run these steps on the controller only
after the PR and its ARM64 fixture pass review.

## Intended layout

Examples below use `chat.example.com` as the server base and `example.com`
as its parent domain. Substitute the existing private `ZULIP_FQDN` and the
corresponding deployment hostnames locally. Keep real values outside this repository.

| Hostname | Organization | Action |
| --- | --- | --- |
| `chat.example.com` | Server base (`EXTERNAL_HOST`) | Keep the setting and original tunnel route |
| `zulip-openops.example.com` | Existing collaboration organization (`openops`) | Move the root organization in place |
| `zulip-projects.example.com` | Personal projects (`projects`) | Create a separate invitation-only organization |

Use **service-organization** for the public names. This groups the Zulip
addresses together in DNS and service inventories while keeping them one label
below the parent domain, covered by the existing wildcard certificate.

The seven-container stack, storage paths and credentials stay the same.
`ZULIP_ORG_HOSTS` lists the exact names Caddy accepts. `ZULIP_REALM_HOSTS` maps
Zulip's internal organization IDs to those public names through `REALM_HOSTS`.
The base `ZULIP_FQDN` remains the server's `EXTERNAL_HOST`.

Preflight checks the two settings together: every custom destination must be in
the Caddy list, destinations must be distinct, and no mapping may shadow
another organization's natural subdomain. Wildcards, unrelated domains, deeper
names and inconsistent mappings fail preflight. The previous single-organization
and default nested-subdomain configurations remain supported.

Organization membership and content are separate. Server administration,
database, storage and availability are shared.

## 1. Inspect the existing organization

```bash
sudo /usr/local/sbin/zulip-compose ps --all
sudo /usr/local/sbin/zulip-compose exec --user zulip \
  --workdir /home/zulip/deployments/current zulip ./manage.py list_realms
```

Expect the special `zulipinternal` entry and the collaboration organization with
an empty `string_id`. The empty value identifies the root organization. Stop if
`openops` or `projects` is already occupied, or if the collaboration organization
has another ID. Never rename `zulipinternal`.

Record the root organization's numerical ID and a private account/message
inventory before changing its subdomain:

```bash
sudo /usr/local/sbin/zulip-compose exec --user zulip \
  --workdir /home/zulip/deployments/current zulip ./manage.py shell -c \
  'from zerver.models import Realm, UserProfile, Message; r=Realm.objects.get(string_id=""); print({"realm_id": r.id, "users": UserProfile.objects.filter(realm=r).count(), "messages": Message.objects.filter(realm=r).count()})'
```

## 2. Confirm the existing certificate covers the names

In Cloudflare's SSL/TLS edge certificate settings, require an **active**
Universal certificate covering `*.example.com`. It covers both
`zulip-openops.example.com` and `zulip-projects.example.com`, as well as the
existing `chat.example.com` base. The chosen first-level layout uses the
existing certificate; no additional Cloudflare subscription is required.

Check the full hostnames and their suffix before publishing them. Keep the
working base address until the new routes pass external TLS checks below.

## 3. Take a protected checkpoint

Complete the [backup and recovery procedure](zulip-controller.md#backup-and-recovery)
before the rename: require a successful fresh dump and preserve uploads,
configuration, credentials and the matching private ingress `.env`. Record the
source revision and images; retain the Cloudflare route/DNS settings privately.
Confirm an independent copy is retrievable. If any checkpoint step fails, stop
the migration and keep the original organization address.

## 4. Prepare routing without moving the organization

Update the controller checkout to the reviewed main revision using the normal
fast-forward procedure. Run the preparation playbook to install the updated
guard. It leaves activation off by default:

```bash
cd /srv/platform
ansible-playbook ansible/playbooks/caddy-public.yml
sudoedit /srv/platform/compose/caddy-public/.env
```

Keep `ZULIP_FQDN` at its existing base value. Add both organization settings,
using the corresponding deployment names. The mapping is a single-line JSON
object inside single quotes:

```dotenv
ZULIP_ORG_HOSTS='zulip-openops.example.com zulip-projects.example.com'
ZULIP_REALM_HOSTS='{"openops":"zulip-openops.example.com","projects":"zulip-projects.example.com"}'
```

Preserve every other setting and all six Zulip secrets. Apply through the
guarded unit, then confirm the original organization still works:

```bash
sudo /usr/local/sbin/zulip-compose config --quiet
sudo /usr/local/sbin/caddy-public-check-storage
sudo systemctl restart caddy-public
sudo /usr/local/sbin/zulip-compose ps --all
```

Confirm the running image received the mapping:

```bash
sudo /usr/local/sbin/zulip-compose exec --user zulip \
  --workdir /home/zulip/deployments/current zulip \
  ./scripts/get-django-setting REALM_HOSTS
```

Require the two intended IDs and matching public hostnames. The official image
generates this setting from `SETTING_REALM_HOSTS` on startup; do not edit the
generated `settings.py` inside the container.

In Cloudflare, add two exact published-application routes to the existing
tunnel. Choose subdomains `zulip-openops` and `zulip-projects` under the parent
domain. Both use Service URL `http://server:8080`. Retain the base route.
Preserve the incoming Host header: do not override both organization routes to
the base hostname. Keep the existing proxy trust settings and private-service
boundaries.

From an external client, check each new hostname without bypassing TLS:

```bash
curl --max-time 20 --silent --show-error --output /dev/null \
  --write-out 'openops HTTP %{http_code}\n' https://zulip-openops.example.com/login/
curl --max-time 20 --silent --show-error --output /dev/null \
  --write-out 'projects HTTP %{http_code}\n' https://zulip-projects.example.com/login/
```

Require exit status zero for each request. A missing-organization response is
expected before creating or moving the organization; it is not functional
acceptance. Resolve certificate errors, Access login walls, tunnel errors or
unexpected redirects to the base before continuing. Do not use `curl -k`.

## 5. Move the existing collaboration organization

Run once after the previous checks pass:

```bash
sudo /usr/local/sbin/zulip-compose exec --user zulip \
  --workdir /home/zulip/deployments/current zulip \
  ./manage.py change_realm_subdomain --realm '' --skip-redirect openops
```

`--realm ''` selects the existing root organization. This changes its subdomain
in place. `--skip-redirect` avoids creating a placeholder organization at the
old root, leaving it available for the rollback below. Existing sessions are
invalidated by Zulip; accounts, messages and organization ID remain in place.

Sign in at `https://zulip-openops.example.com` with the existing account.
The old base session has been invalidated by the move. Repeat the inventory
command from step 1 with `string_id="openops"`. Require the same numerical organization ID and the
expected account/message counts before sending new test messages. Verify an
existing message and upload if present, then send a new message and small upload.
Do not rerun the rename blindly if a check fails.

## 6. Create the projects organization

```bash
sudo /usr/local/sbin/zulip-compose exec --user zulip \
  --workdir /home/zulip/deployments/current zulip \
  ./manage.py generate_realm_creation_link
```

Open the full single-use link privately. When asked for the subdomain, enter
**projects**, the internal ID used as the mapping key. Zulip maps that ID to
`zulip-projects.example.com`. Enter the intended display name and select
invitation-only signup. Create its owner account and verify
`https://zulip-projects.example.com`. Do not enter the full hostname or
`zulip-projects` as the internal ID, and do not leave it blank.

Run `list_realms` again. Require separate `openops` and `projects` entries and no
active root organization. Sign into both in separate browser tabs, then add both
addresses to the native client. Accounts are organization-specific even if the
same email address is used.

Before inviting a collaborator, verify that each organization's channels,
messages, uploads and bot configuration are scoped to that organization. Test
cellular access and HTTP-to-HTTPS redirects separately for each address. Repeat
the private Forgejo availability check and record controller resource use.

## Roll back the organization address

If the original organization was moved with `--skip-redirect`, the base remains
free. After inspecting `list_realms`, move that same organization back:

```bash
sudo /usr/local/sbin/zulip-compose exec --user zulip \
  --workdir /home/zulip/deployments/current zulip \
  ./manage.py change_realm_subdomain --realm openops --skip-redirect ''
```

Sign in again at the original base address and verify the preserved
organization ID. Set both `ZULIP_ORG_HOSTS=` and `ZULIP_REALM_HOSTS=`, then
restart the guarded unit to withdraw the additional mappings and Caddy routes.
Remove only the two added Cloudflare published applications and their corresponding DNS records once rollback is
accepted; retain the base route.

If `projects` was already created, its data remains in the database but its
public route is withdrawn. Do not delete it as part of address rollback. Stop
and investigate if the root is occupied or the command fails; do not delete a
realm or restore a database merely to free a hostname.

## Acceptance record

| Check | Required evidence |
| --- | --- |
| Certificate and routing | Both names verify TLS externally and reach the intended application |
| Existing organization | Same numerical ID, expected accounts/messages and working uploads |
| Separation | Mapped hostnames select distinct `openops` and `projects` memberships, content and bot destinations |
| Clients | Both sessions work concurrently; native/cellular checks pass |
| Operations | All seven containers healthy/running as applicable; Forgejo stays available |
| Recovery | Protected checkpoint and address rollback result recorded separately |

The ARM64 fixture verifies that the image applies the hostname mapping, then
exercises a disposable rename, rollback, preserved account/message/API key,
both mapped login pages and cross-organization credential rejection. It does
not establish production DNS, edge certificates, live clients or recovery.

## Sources

- [Zulip 13.2 multiple organizations](https://zulip.readthedocs.io/en/13.2/production/multiple-organizations.html)
- [Version-matched rename command](https://github.com/zulip/zulip/blob/13.2/zerver/management/commands/change_realm_subdomain.py)
- [Version-matched rename implementation](https://github.com/zulip/zulip/blob/13.2/zerver/actions/create_realm.py)
- [Cloudflare Universal SSL coverage](https://developers.cloudflare.com/ssl/edge-certificates/universal-ssl/)
- [Cloudflare Tunnel published-application routes](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel/)
