# Gitea to Forgejo Migration

Status: Forgejo operational LAN cutover verified: HTTP/3000 health, SSH/2223, post-cutover source parity, full OCI retrieval, native Actions and Kuma availability passed. Legacy state is retained for rollback; remaining review is listed in section 9.
Recorded source: Gitea 1.27.3. Target: Forgejo 15.0.11 LTS.

## Recorded progress — 2026-11-18

- [x] Consistent legacy checkpoint verified at `/srv/backups/gitea-before-forgejo-20261118T002504Z-6vyfHG`; both legacy services restarted.
- [x] Off-device transfer archive checksum verified: `23b1545d587cef77b8c7cd931aa26b00c830a29d8178153b3693f69de42b7b53` for `gitea-forgejo-transfer-20261118T002504Z.tar.gz`; operator reports it stored in private `homelab-backups-collection`.
- [x] Ignored legacy Compose directories restored after updating the controller checkout.
- [x] `git.lab.home.arpa` and `forgejo.lab.home.arpa` resolve to `10.0.0.50`; staging ports selected as HTTP/3002 and SSH/2223.
- [x] Forgejo installer completed; signed in as `ctalaveraw` at `http://forgejo.lab.home.arpa:3002/`.
- [x] Source inventory: one mirrored repository and one container package/version; no issues, PRs, comments, releases, attachments or LFS objects recorded. The legacy source repository was public; the intended Forgejo mirror is private.
- [x] Forgejo mirror created as `ctalaveraw/arm-homelab-platform`; `platform-hello` copied from Gitea and associated with that repository.
- [x] OCI tag `1ddd76c14a35f974d06dbd1ed7e3c4c14475c92d` retained; source/destination digest `sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e` matched and full retrieval passed.
- [x] Fresh runner deployed with Ansible (`ok=13`, `changed=3`, `failed=0`), moved to repository scope, and exercised by the native workflow. User-scoped registration removed.
- [x] Controller local `main`, GitHub and Forgejo HTTP parity matched `eb84e2ec9c7d72bd99931350f018120b0ef5830f`; SSH read through alias `forgejo` returned the same HEAD/main.
- [x] First TCP/3000 attempt safely rolled back after the anonymous version API returned HTTP 403. Staging `/api/healthz` then returned HTTP 200 with cache/database checks passing.
- [x] Legacy units stopped and disabled; Forgejo `/api/healthz` passed at `http://git.lab.home.arpa:3000/`; runner active after the successful retry.
- [x] Port-change rollback checkpoint retained at `/srv/backups/forgejo-port3000-retry-fEuVxI`. Initial connection refusals during startup were followed by a passing health check.
- [x] Final-address OCI login and full retrieval passed at `git.lab.home.arpa:3000` for the same qualified digest; no artifact rebuild or re-copy was needed.
- [x] Post-cutover source parity passed: local `main`, local HEAD, GitHub and Forgejo all matched `44d3d82ba9919c39407031ded42abd4ff49b2128` using the fetch-only Forgejo remote.
- [x] Native Actions screenshots confirm run #1 (manual, commit `eb84e2ec9c`, 2m47s) and run #2 (push, commit `44d3d82ba9`, 2m32s) succeeded.
- [x] Kuma screenshot shows monitor `Forgejo` Up at `http://git.lab.home.arpa:3000/`. The monitor checks the root URL; changing it to `/api/healthz` remains a recommended improvement.
- [ ] Generated URLs, destination permissions and remaining metadata reviewed before retiring the legacy state.

The record distinguishes staging results from post-cutover checks. Final-address HTTP health, service activation, Git source parity, complete OCI retrieval, native workflow success and Kuma availability have now passed. The [consumer checks](forgejo-reference-map.md#update-consumers-after-transfer) remain a reusable reference. The steps below remain the reusable migration/rollback procedure; this controller has already completed the port change and should keep its existing local `.env` and separate state.

## Migration method

Use a fresh Forgejo instance beside Gitea. The [supported database conversion](https://forgejo.org/docs/v15.0/admin/upgrade/from-gitea/) only covers Gitea through 1.22 via Forgejo 10. Do not point this Forgejo image at the existing Gitea directory or copy its SQLite database, `app.ini`, secrets or runner identity.

| Resource | Gitea | Forgejo staging | Forgejo after cutover |
| --- | --- | --- | --- |
| Compose project | `gitea` | `forgejo` | `forgejo` |
| Application state | `services/gitea` | `services/forgejo` | Unchanged |
| Runner state | `services/gitea-runner` | `services/forgejo-runner` | Unchanged |
| Host HTTP port | `3000` | `3002` | `3000` |
| Host Git SSH port | `2222` | `2223` | `2223` |
| Lifecycle units | `gitea`, `gitea-runner` | `forgejo`, `forgejo-runner` | Unchanged |

Port 3001 belongs to Uptime Kuma. If an earlier local Forgejo `.env` uses 3001, change both `FORGEJO_HTTP_PORT` and the port in `FORGEJO_ROOT_URL` to 3002 before startup.

State paths are relative to `/srv/storage/state`. HTTP port 3002 is temporary for parallel validation. After migration, Forgejo takes over the controller's LAN TCP/3000 once Gitea is stopped and disabled. The container's HTTP listener remains 3000 throughout; only the host mapping and advertised root URL change.

The checked-in Forgejo `.env.example` retains the staging values. Current controller overrides are `FORGEJO_FQDN=git.lab.home.arpa`, `FORGEJO_ROOT_URL=http://git.lab.home.arpa:3000/` and `FORGEJO_HTTP_PORT=3000`; the LAN bind addresses and SSH/2223 remain unchanged.

## 1. Checkpoint before updating the controller checkout

Run from the old `/srv/platform` checkout while its legacy manifests still exist. Confirm actual Gitea version, available SD space and inventory all repositories, local-only branches, issues/PRs, wikis, releases, attachments, packages, accounts, hooks, access keys, tokens, secrets and mirror settings. GitHub mirroring alone does not protect these.

```bash
cd /srv/platform
docker-compose --env-file compose/gitea/.env -f compose/gitea/compose.yml exec -T -u git server gitea --version </dev/null
df -h /srv/storage/state /srv/backups
git status --short
```

Create a private local checkpoint of the old manifests (including local `.env`), units and guards. Then stop both legacy services briefly for a consistent filesystem/SQLite snapshot:

```bash
umask 077
checkpoint="/srv/backups/gitea-before-forgejo-$(date -u +%Y%m%dT%H%M%SZ)"
sudo install -d -m 0700 "$checkpoint"
sudo cp -a compose/gitea compose/gitea-runner "$checkpoint/"
sudo cp -a /etc/systemd/system/gitea.service /etc/systemd/system/gitea-runner.service "$checkpoint/"
sudo cp -a /usr/local/sbin/gitea-check-storage /usr/local/sbin/gitea-runner-check-storage "$checkpoint/"
sudo systemctl stop gitea-runner.service gitea.service
sudo tar --acls --xattrs --numeric-owner -C /srv/storage/state/services -cpf "$checkpoint/gitea-state.tar" gitea gitea-runner
sudo systemctl start gitea.service gitea-runner.service
sudo sha256sum "$checkpoint/gitea-state.tar" | sudo tee "$checkpoint/gitea-state.sha256"
```

If snapshot creation fails, restart the original services and resolve it before continuing. This is a local checkpoint, not an off-device backup. Copy it to an independent trusted machine/storage and verify its checksum before retiring Gitea. It contains credentials and private data; keep it out of this public repository. The separate private backup collection is not an application-state directory; routine encrypted backup and restore acceptance remain separate work.

## 2. Update code and retain legacy rollback manifests

Use the reviewed GitHub revision. Do not overwrite uncommitted work. The revision removes tracked Gitea deployment paths, so restore the checkpoint's two legacy Compose directories to their original local paths before stopping or restarting Gitea again:

```bash
# After updating the checkout, with checkpoint set to the path above:
sudo cp -a "$checkpoint/gitea" "$checkpoint/gitea-runner" /srv/platform/compose/
```

Those paths are now ignored, local-only rollback inputs. Existing installed units and guards continue to reference them. Do not rename the legacy state directories. Do not run `docker system prune` or delete old images during the transition.

## 3. Start the separate Forgejo instance

Check `ip -4 route` and Docker network subnets before using candidate ingress range `172.30.250.0/28`; inspect VPN routes too. Select a non-overlapping range and fixed proxy/server addresses if needed. Keep the Caddy address identical in both `.env` files.

```bash
cp compose/forgejo/.env.example compose/forgejo/.env
chmod 600 compose/forgejo/.env
```

Populate the controller LAN bind addresses. Add an INNER DNS record for `forgejo.lab.home.arpa` pointing at the controller, or use an equivalent temporary workstation hosts entry. Keep `FORGEJO_ROOT_URL` consistent with that hostname and `:3002/`.

```bash
.ci-venv/bin/ansible-playbook ansible/playbooks/02-forgejo.yml --ask-become-pass
curl --fail --silent --show-error http://forgejo.lab.home.arpa:3002/api/healthz
```

Complete initial installation over the trusted LAN and create administrator `ctalaveraw`. The installer reserves `admin`; leave that username on the legacy source and use the new owner for Forgejo destinations. Self-registration is disabled and anonymous repository viewing requires sign-in. Forgejo remains LAN/WireGuard-only; do not add a WAN forwarding rule for it. Verify the UI reports Forgejo and the expected version; check unit/container logs if it does not become ready.

The rootful image's default SQLite path `/data/gitea/gitea.db` belongs inside the new Forgejo `/data` mount. Keep this internal path; it is not permission to reuse `/srv/storage/state/services/gitea`.

Use `/api/healthz` for readiness: require HTTP 200 and JSON `status: pass`. With `REQUIRE_SIGNIN_VIEW=true`, anonymous version API requests can return HTTP 403; this is an authentication rejection, not a suitable startup test. Keep sign-in protection enabled. Query `/api/v1/version` with authentication if version information is needed.

## 4. Populate source and application data

Recreate the private one-way pull mirror from canonical `https://github.com/ctalaveraw/arm-homelab-platform`, including required credentials and sync interval. Select destination owner `ctalaveraw`, repository name `arm-homelab-platform`, private visibility and pull-mirror mode. Its staging path is `http://forgejo.lab.home.arpa:3002/ctalaveraw/arm-homelab-platform`; the legacy `admin/...` owner path is not the Forgejo destination.

For local-only repository data, use Forgejo's Gitea migration UI with selected metadata and a temporary narrowly scoped source token. Authenticate to Gitea with the source account `admin`, then select `ctalaveraw` as the Forgejo destination owner. Inventory first: a GitHub pull mirror alone does not import Gitea-only issues, wikis, releases or attachments, and a separate full import must not overwrite the same destination name. Choose the import/mirror treatment per repository before creating it. Check migration results; account identities, authentication providers, secrets and packages require separate handling.

Recreate hooks, deploy keys, SSH keys, permissions and integrations deliberately. Tokens and runner identities belong to the new instance. Compare branch/tag refs and review imported issues, wiki pages, releases and attachments before declaring data transfer complete.

For a LAN Gitea import, permit only its exact hostname in Forgejo migration settings if the private-address filter blocks it. Do not disable private-address protection globally. A canonical GitHub mirror does not need this exception.

## 5. Replicate required OCI artifacts

Authenticate interactively as `ctalaveraw` with a new Forgejo credential using Skopeo and a private authfile outside Git. Use the new owner with the existing package name and qualified source digest:

```bash
install -d -m 0700 "$HOME/.config/containers"
skopeo login --username ctalaveraw --tls-verify=false --authfile "$HOME/.config/containers/forgejo-auth.json" forgejo.lab.home.arpa:3002
```

Set `SOURCE_IMAGE` to the qualified `docker://ghcr.io/ctalaveraw/platform-hello@sha256:...` reference and `DEST_IMAGE` to `docker://forgejo.lab.home.arpa:3002/ctalaveraw/platform-hello:TAG`, then:

```bash
DEST_AUTHFILE="$HOME/.config/containers/forgejo-auth.json" DEST_TLS_VERIFY=false \
  bash scripts/ops/replicate-oci-image.sh "$SOURCE_IMAGE" "$DEST_IMAGE"
DEST_AUTHFILE="$HOME/.config/containers/forgejo-auth.json" DEST_TLS_VERIFY=false \
  bash scripts/ops/verify-oci-parity.sh "$SOURCE_IMAGE" "$DEST_IMAGE"
AUTHFILE="$HOME/.config/containers/forgejo-auth.json" TLS_VERIFY=false \
  bash scripts/ops/verify-oci-retrieval.sh "$DEST_IMAGE"
```

The HTTP-only flags apply to the trusted LAN endpoint, including final LAN HTTP/3000 until private HTTPS is deployed. Use TLS verification after HTTPS acceptance. Associate packages with `ctalaveraw/arm-homelab-platform` using `scripts/ops/link-forgejo-package.sh`, owner argument `ctalaveraw`, and a new `FORGEJO_TOKEN`. Do not rebuild images to transfer them. Inventory non-container packages separately; these scripts do not transfer them.

## 6. Register the restricted validation runner

```bash
docker build -t localhost/platform-forgejo-runner:dev images/forgejo-runner
cp compose/forgejo-runner/.env.example compose/forgejo-runner/.env
sudo install -d -o 10001 -g 10001 -m 0700 /srv/storage/state/services/forgejo-runner
sudo install -o 10001 -g 10001 -m 0600 compose/forgejo-runner/runner.yml.example /srv/storage/state/services/forgejo-runner/runner.yml
```

In the mirrored repository, open **Settings → Units → Overview**, check **Actions** and save. Forgejo's default mirror units omit Actions. Then create a new runner under **repository Settings → Actions → Runners**; user, organization and instance registrations have broader scope. Put its UUID/token into the private `runner.yml` with a local editor. The internal URL is `http://forgejo:3000/`; the label is `r5c-arm64-validation:host`. See [official registration](https://forgejo.org/docs/latest/admin/actions/registration/).

```bash
.ci-venv/bin/ansible-playbook ansible/playbooks/03-forgejo-runner.yml --ask-become-pass
```

Force mirror synchronization and confirm `.forgejo/workflows/platform-ci.yml` runs successfully on the ARM64 UID-10001 worker with no production Docker socket. Test a subsequent mirrored push as well. The old Gitea `.runner` identity is not valid here.

## 7. Move LAN HTTP to port 3000

Perform the data transfer and staging acceptance first. Freeze legacy writes during the final synchronization. The intended LAN endpoint after cutover is `http://git.lab.home.arpa:3000/`; `git.lab.home.arpa` must resolve to the controller. This port change does not transfer or alter application data.

Before stopping services, verify the existing staging endpoint:

```bash
curl --noproxy '*' --fail --silent --show-error http://forgejo.lab.home.arpa:3002/api/healthz
```

Require HTTP 200 and JSON `status: pass` before proceeding. After restart, use the same health endpoint on TCP/3000; do not use an anonymous version API request as readiness.

If the Forgejo runner has been installed, stop it first. Save a private copy of Forgejo's current `.env` before editing. Then stop the staged server and disable the old units so they cannot reclaim TCP/3000 after reboot:

```bash
cp -n compose/forgejo/.env compose/forgejo/.env.before-lan-port-cutover
sudo systemctl stop forgejo.service
sudo systemctl disable --now gitea-runner.service gitea.service
sudo ss -lntp '( sport = :3000 )'
```

Verify that the chosen controller LAN address and TCP/3000 are free. Update `compose/forgejo/.env`:

```text
FORGEJO_FQDN=git.lab.home.arpa
FORGEJO_ROOT_URL=http://git.lab.home.arpa:3000/
FORGEJO_HTTP_PORT=3000
```

Keep the LAN bind addresses, new state directory and SSH port unchanged. Validate the configuration and start the service explicitly; Ansible `state: started` alone does not recreate a running container:

```bash
docker-compose --env-file compose/forgejo/.env -f compose/forgejo/compose.yml config --quiet
sudo systemctl start forgejo.service
curl --fail --retry 10 --retry-connrefused --retry-delay 2 --max-time 3 http://git.lab.home.arpa:3000/api/healthz
```

Restart the Forgejo runner if installed. Its internal server URL `http://forgejo:3000/` is unchanged. Verify generated clone/package URLs, Git operations and OCI retrieval at the final LAN endpoint. Update Kuma, registry authfiles, fetch-only remotes, hooks and bookmarks for the final URL. GitHub/GHCR and Flux references remain unchanged.

For a port-cutover failure, restore the saved staging `.env` and restart Forgejo on TCP/3002. Only after it has released TCP/3000 should the old Gitea units be re-enabled and started. Reconcile new writes before a full application fallback; never point Gitea at Forgejo data.

## 8. Private HTTPS

Forgejo remains LAN/WireGuard-only. Follow the private-access sections of [domain ingress](domain-ingress.md) for a registered hostname and DNS-01 certificates. The checked-in Caddyfile is a public ACME profile; it must be adapted before private certificate deployment. No WAN forwarding to Forgejo is part of this migration. HTTPS clients later use TCP/443 independently of the retained backend port.

## 9. Acceptance and retention

- [x] Consistent backup copied off-device and checksum verified.
- [x] Actual source version and data inventory recorded.
- [ ] Forgejo UI, administrator login, permissions and required account authentication work.
- [ ] Required repository refs, metadata, wiki, releases and attachments accounted for.
- [x] Staging main-branch parity, SSH read and locally verified SSH host key recorded.
- [x] Required OCI digest parity, full retrieval and package association passed during staging.
- [x] Forgejo final LAN TCP/3000 health passed; runner service active.
- [x] Legacy Gitea units stopped and disabled, releasing TCP/3000.
- [x] Final-address OCI retrieval passed at LAN TCP/3000 with the preserved digest.
- [x] Post-cutover source parity passed across controller-local, GitHub and Forgejo `main`.
- [ ] Generated root/clone/package URLs agree with the final address.
- [x] Native Forgejo validation succeeded in manual and push-triggered runs.
- [x] Kuma availability check targets Forgejo at the final root URL and reports Up.
- [ ] Notification delivery for the Forgejo monitor verified independently.
- [ ] Both new service lifecycles and guarded storage behavior checked on the host.
- [ ] Rollback routing and the preserved legacy instance checked before final retirement.

The Kuma screenshot establishes current root-URL availability, not alert delivery or use of the JSON health endpoint. Its historical uptime percentages include the existing monitor's earlier history and are not a Forgejo-only availability measurement.

The old Gitea units stay disabled after the port cutover. Retain their state, images, private checkpoint and local rollback manifests for an agreed retention period. Do not remove them automatically.

Private HTTPS certificate, redirect and LAN/WireGuard acceptance are separate follow-up work when HTTPS is deployed; they do not block the current private LAN HTTP migration. A reboot-safe startup test and a full backup restoration are separate from the recorded port-change rollback.

## Rollback

Before cutover, stop the new services and continue using the existing Gitea URLs; its state was never converted. After cutover, record any new Forgejo writes first: an old-instance fallback does not transfer them back.

Stop Caddy and the Forgejo runner before stopping Forgejo (Caddy uses its ingress network). Start the preserved Gitea units, restore the prior DNS/client/monitor endpoints, and verify Git access and the old runner. The saved state archive is a restore option only if the untouched legacy state is unavailable; never overlay a live database.

No step requires downgrading a database or running Gitea against Forgejo state.
