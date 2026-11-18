# Gitea to Forgejo Migration

Status: repository configuration prepared; no host migration acceptance recorded.
Recorded source: Gitea 1.27.3. Target: Forgejo 15.0.11 LTS.

## Migration method

Use a fresh Forgejo instance beside Gitea. The [supported database conversion](https://forgejo.org/docs/v15.0/admin/upgrade/from-gitea/) only covers Gitea through 1.22 via Forgejo 10. Do not point this Forgejo image at the existing Gitea directory or copy its SQLite database, `app.ini`, secrets or runner identity.

| Resource | Gitea | Forgejo staging |
| --- | --- | --- |
| Compose project | `gitea` | `forgejo` |
| Application state | `services/gitea` | `services/forgejo` |
| Runner state | `services/gitea-runner` | `services/forgejo-runner` |
| Host HTTP port | `3000` | `3001` |
| Host Git SSH port | `2222` | `2223` |
| Lifecycle units | `gitea`, `gitea-runner` | `forgejo`, `forgejo-runner` |

State paths are relative to `/srv/storage/state`. Keeping staging ports is acceptable after migration; HTTPS clients use TCP/443 regardless of the backend port.

## 1. Checkpoint before updating the controller checkout

Run from the old `/srv/platform` checkout while its legacy manifests still exist. Confirm actual Gitea version, available SD space and inventory all repositories, local-only branches, issues/PRs, wikis, releases, attachments, packages, accounts, hooks, access keys, tokens, secrets and mirror settings. GitHub mirroring alone does not protect these.

```bash
cd /srv/platform
docker-compose --env-file compose/gitea/.env -f compose/gitea/compose.yml exec -T -u git server gitea --version
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

If snapshot creation fails, restart the original services and resolve it before continuing. This is a local checkpoint, not an off-device backup. Copy it to an independent trusted machine/storage and verify its checksum before retiring Gitea. It contains credentials and private data; never commit it.

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

Populate the controller LAN bind addresses. Add an INNER DNS record for `forgejo.lab.home.arpa` pointing at the controller, or use an equivalent temporary workstation hosts entry. Keep `FORGEJO_ROOT_URL` consistent with that hostname and `:3001/`.

```bash
ansible-playbook ansible/playbooks/02-forgejo.yml --ask-become-pass
curl --fail --silent --show-error http://forgejo.lab.home.arpa:3001/api/v1/version
```

Complete initial installation over the trusted LAN and create the administrator. Self-registration is disabled and anonymous repository viewing requires sign-in. Do not enable WAN forwarding before initialization and acceptance. Verify the UI reports Forgejo and the expected version; check unit/container logs if it does not become ready.

## 4. Populate source and application data

Recreate the private one-way pull mirror from canonical GitHub, including required credentials and sync interval. Preserve the owner/repository naming used by consumers where practical. For local-only repository data, use Forgejo's Gitea migration UI with selected metadata and a temporary narrowly scoped token. Check migration results per repository; account identities, authentication providers, secrets and packages require separate handling.

Recreate hooks, deploy keys, SSH keys, permissions and integrations deliberately. Tokens and runner identities belong to the new instance. Compare branch/tag refs and review imported issues, wiki pages, releases and attachments before declaring data transfer complete.

For a LAN Gitea import, permit only its exact hostname in Forgejo migration settings if the private-address filter blocks it. Do not disable private-address protection globally. A canonical GitHub mirror does not need this exception.

## 5. Replicate required OCI artifacts

Authenticate interactively with Skopeo into a private authfile outside Git. Use the original owner/package identity and the qualified source digest. For example:

```bash
skopeo login --tls-verify=false --authfile "$HOME/.config/containers/forgejo-auth.json" forgejo.lab.home.arpa:3001
```

Set `SOURCE_IMAGE` to the qualified `docker://ghcr.io/...@sha256:...` reference and `DEST_IMAGE` to `docker://forgejo.lab.home.arpa:3001/OWNER/PACKAGE:TAG`, then:

```bash
DEST_AUTHFILE="$HOME/.config/containers/forgejo-auth.json" DEST_TLS_VERIFY=false \
  bash scripts/ops/replicate-oci-image.sh "$SOURCE_IMAGE" "$DEST_IMAGE"
DEST_AUTHFILE="$HOME/.config/containers/forgejo-auth.json" DEST_TLS_VERIFY=false \
  bash scripts/ops/verify-oci-parity.sh "$SOURCE_IMAGE" "$DEST_IMAGE"
AUTHFILE="$HOME/.config/containers/forgejo-auth.json" TLS_VERIFY=false \
  bash scripts/ops/verify-oci-retrieval.sh "$DEST_IMAGE"
```

The HTTP-only flags apply to this trusted LAN staging endpoint. Use TLS verification after domain cutover. Associate packages with their source repository using `scripts/ops/link-forgejo-package.sh` and a new `FORGEJO_TOKEN`. Do not rebuild images to transfer them. Inventory non-container packages separately; these scripts do not transfer them.

## 6. Register the restricted validation runner

```bash
docker build -t localhost/platform-forgejo-runner:dev images/forgejo-runner
cp compose/forgejo-runner/.env.example compose/forgejo-runner/.env
sudo install -d -o 10001 -g 10001 -m 0700 /srv/storage/state/services/forgejo-runner
sudo install -o 10001 -g 10001 -m 0600 compose/forgejo-runner/runner.yml.example /srv/storage/state/services/forgejo-runner/runner.yml
```

In the mirrored repository, enable Actions and create a new runner under **repository Settings → Actions → Runners**, not instance scope. Put its UUID/token into the private `runner.yml` with a local editor. The internal URL is `http://forgejo:3000/`; the label is `r5c-arm64-validation:host`. See [official registration](https://forgejo.org/docs/latest/admin/actions/registration/).

```bash
ansible-playbook ansible/playbooks/03-forgejo-runner.yml --ask-become-pass
```

Force mirror synchronization and confirm `.forgejo/workflows/platform-ci.yml` runs successfully on the ARM64 UID-10001 worker with no production Docker socket. Test a subsequent mirrored push as well. The old Gitea `.runner` identity is not valid here.

## 7. Add HTTPS and switch consumers

Follow [domain ingress](domain-ingress.md). Use a product-independent hostname such as `git.<registered-domain>`, update Forgejo's root URL and SSH domain, and recreate the containers explicitly. Update the fetch-only Git remote, Kuma checks, OCI authfiles/clients, hooks and bookmarks. Keep GHCR/Flux source and workload references unchanged unless a separate delivery change is intended.

## 8. Acceptance and retirement

- [ ] Consistent backup copied off-device and checksum verified.
- [ ] Actual source version and data inventory recorded.
- [ ] Forgejo UI, administrator login, permissions and required account authentication work.
- [ ] Required repository refs, metadata, wiki, releases and attachments accounted for.
- [ ] Git HTTP clone and intended SSH operations pass; new SSH host key verified locally.
- [ ] GitHub mirror sync, source parity and native Forgejo validation pass.
- [ ] Required OCI digest parity, full retrieval and package association pass.
- [ ] HTTPS certificate, redirect, root/clone URLs and LAN/WireGuard behavior pass.
- [ ] Availability checks and alerts now target Forgejo accurately.
- [ ] Both new service lifecycles and guarded storage behavior checked on the host.
- [ ] Rollback routing and the preserved legacy instance checked before final retirement.

After those checks, disable/stop `gitea-runner.service` and `gitea.service`. Retain their state, images, private checkpoint and local rollback manifests for an agreed retention period. Do not remove them automatically.

## Rollback

Before cutover, stop the new services and continue using the existing Gitea URLs; its state was never converted. After cutover, record any new Forgejo writes first: an old-instance fallback does not transfer them back.

Stop Caddy and the Forgejo runner before stopping Forgejo (Caddy uses its ingress network). Start the preserved Gitea units, restore the prior DNS/client/monitor endpoints, and verify Git access and the old runner. The saved state archive is a restore option only if the untouched legacy state is unavailable; never overlay a live database.

No step requires downgrading a database or running Gitea against Forgejo state.
