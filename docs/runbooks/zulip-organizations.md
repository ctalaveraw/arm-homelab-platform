# Move Zulip to separate organization hostnames

Status: source preparation. No controller migration or Cloudflare certificate
acceptance is recorded by this change. Run these steps on the controller only
after the PR and its ARM64 fixture pass review.

## Intended layout

Examples below use `chat.example.com`; substitute the existing private
`ZULIP_FQDN` value locally. Keep real deployment values outside this repository.

| Hostname | Organization | Action |
| --- | --- | --- |
| `chat.example.com` | Server base (`EXTERNAL_HOST`) | Keep the setting and original tunnel route |
| `openops.chat.example.com` | Existing collaboration organization | Move the root organization in place |
| `projects.chat.example.com` | Personal projects | Create a separate invitation-only organization |

The seven-container stack, storage paths and credentials stay the same.
`ZULIP_ORG_HOSTS` adds exact Caddy host matches. Each entry must be a distinct
direct subdomain of the base; wildcards, deeper names and other domains fail
preflight. Zulip selects the organization from the forwarded hostname. These
nested names use Zulip's normal subdomain handling; no `REALM_HOSTS` mapping is
needed.

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

## 2. Confirm browser-facing certificate coverage

In Cloudflare's SSL/TLS edge certificate settings, require an **active**
certificate covering both planned hostnames or `*.chat.example.com`. An active
certificate for `*.example.com` does not cover them.

On a normal full-zone Cloudflare setup, deeper names require an advanced
certificate or Total TLS. A partial CNAME setup has different issuance rules.
Keep any subscription purchase a separate account-owner decision; this PR
neither orders certificates nor changes billing. An origin certificate on Caddy
cannot replace missing browser-to-Cloudflare certificate coverage.

Do not rename the live organization while certificate coverage is pending. If
the account cannot provide the required certificate, keep the working URL and
revisit the hostname plan before continuing.

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

Keep `ZULIP_FQDN` at its existing base value. Add only the organization-host
setting, using the corresponding deployment names:

```dotenv
ZULIP_ORG_HOSTS='openops.chat.example.com projects.chat.example.com'
```

Preserve every other setting and all six Zulip secrets. Apply through the
guarded unit, then confirm the original organization still works:

```bash
sudo /usr/local/sbin/zulip-compose config --quiet
sudo /usr/local/sbin/caddy-public-check-storage
sudo systemctl restart caddy-public
sudo /usr/local/sbin/zulip-compose ps --all
```

In Cloudflare, add two exact published-application routes to the existing
tunnel. Both use Service URL `http://server:8080`. Retain the base route.
Preserve the incoming Host header: do not override both organization routes to
the base hostname. Keep the existing proxy trust settings and private-service
boundaries.

From an external client, check each new hostname without bypassing TLS:

```bash
curl --max-time 20 --silent --show-error --output /dev/null \
  --write-out 'openops HTTP %{http_code}\n' https://openops.chat.example.com/login/
curl --max-time 20 --silent --show-error --output /dev/null \
  --write-out 'projects HTTP %{http_code}\n' https://projects.chat.example.com/login/
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

Clear cookies/site data for the old base hostname, then sign in at
`https://openops.chat.example.com`. Repeat the inventory command from step 1
with `string_id="openops"`. Require the same numerical organization ID and the
expected account/message counts before sending new test messages. Verify an
existing message and upload if present, then send a new message and small upload.
Do not rerun the rename blindly if a check fails.

## 6. Create the projects organization

```bash
sudo /usr/local/sbin/zulip-compose exec --user zulip \
  --workdir /home/zulip/deployments/current zulip \
  ./manage.py generate_realm_creation_link
```

Open the full single-use link privately. Choose the **projects** subdomain and
the intended display name. Do not leave the subdomain blank or create another
organization at the root. Select invitation-only signup, create its owner
account and verify `https://projects.chat.example.com`.

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

Clear the new and old hostname cookies, then verify the original address and
the preserved organization ID. Set `ZULIP_ORG_HOSTS=` and restart the guarded
unit to withdraw the added Caddy routes. Remove only the two added Cloudflare
published applications and their corresponding DNS records once rollback is
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
| Separation | Distinct `openops` and `projects` memberships, content and bot destinations |
| Clients | Both sessions work concurrently; native/cellular checks pass |
| Operations | All seven containers healthy/running as applicable; Forgejo stays available |
| Recovery | Protected checkpoint and address rollback result recorded separately |

The ARM64 fixture exercises a disposable rename, rollback, preserved account and
message, both login pages and cross-organization credential rejection. It does
not establish production DNS, edge certificates, live clients or recovery.

## Sources

- [Zulip 13.2 multiple organizations](https://zulip.readthedocs.io/en/13.2/production/multiple-organizations.html)
- [Version-matched rename command](https://github.com/zulip/zulip/blob/13.2/zerver/management/commands/change_realm_subdomain.py)
- [Version-matched rename implementation](https://github.com/zulip/zulip/blob/13.2/zerver/actions/create_realm.py)
- [Cloudflare Universal SSL coverage](https://developers.cloudflare.com/ssl/edge-certificates/universal-ssl/)
- [Cloudflare Tunnel routes and multi-level certificate requirement](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel/)
