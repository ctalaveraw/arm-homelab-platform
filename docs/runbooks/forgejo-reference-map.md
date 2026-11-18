# Forgejo Names, Paths and Client Cutover

Updated 2026-11-17. Forgejo is initialized at `http://forgejo.lab.home.arpa:3002/`, and the operator has signed in as `ctalaveraw`. The dashboard still shows zero repositories. Repository transfer, OCI replication, runner acceptance and the final port cutover remain pending.

## Service and account identity

GitHub remains canonical at `https://github.com/ctalaveraw/arm-homelab-platform`. The controller checkout remains `/srv/platform`; its canonical remote is named `github`.

The Forgejo administrator and destination owner is **`ctalaveraw`**. The installer rejects `admin` as a reserved username. Continue authenticating to the old Gitea source with its existing `admin` account, but select `ctalaveraw` as the owner when creating or migrating into Forgejo. Account credentials, tokens and runner registrations belong to their respective instances.

Both LAN names resolve to controller IPv4 `10.0.0.50`. Apply the final values only in [migration step 7](gitea-to-forgejo.md#7-move-lan-http-to-port-3000).

| Setting or consumer | Forgejo staging | Final LAN target |
| --- | --- | --- |
| `FORGEJO_FQDN` | `forgejo.lab.home.arpa` | `git.lab.home.arpa` |
| `FORGEJO_ROOT_URL` | `http://forgejo.lab.home.arpa:3002/` | `http://git.lab.home.arpa:3000/` |
| `FORGEJO_BIND_IP` / `FORGEJO_SSH_BIND_IP` | `10.0.0.50` | `10.0.0.50` |
| `FORGEJO_HTTP_PORT` | `3002` | `3000` |
| `FORGEJO_SSH_PORT` | `2223` | `2223` |
| Repository HTTP clone | `http://forgejo.lab.home.arpa:3002/ctalaveraw/arm-homelab-platform.git` | `http://git.lab.home.arpa:3000/ctalaveraw/arm-homelab-platform.git` |
| Repository SSH clone | `ssh://git@forgejo.lab.home.arpa:2223/ctalaveraw/arm-homelab-platform.git` | `ssh://git@git.lab.home.arpa:2223/ctalaveraw/arm-homelab-platform.git` |
| OCI image prefix | `forgejo.lab.home.arpa:3002/ctalaveraw/platform-hello` | `git.lab.home.arpa:3000/ctalaveraw/platform-hello` |
| Package owner and repository | `ctalaveraw/platform-hello` → `ctalaveraw/arm-homelab-platform` | Same owner and names |
| Runner and Caddy backend | `http://forgejo:3000/` | `http://forgejo:3000/` |

Old Gitea paths such as `admin/arm-homelab-platform` and `admin/platform-hello` identify the source only. Update the owner component as well as the hostname and port in destination URLs. Git history and the qualified OCI digest are preserved by transfer; credentials and old URLs are not automatically redirected between instances.

Forgejo stays LAN/WireGuard-only. Port 3001 belongs to Uptime Kuma. A later registered-domain HTTPS route needs its own private-access configuration; no WAN forwarding is required for this migration. Public Zulip ingress is separate work.

## Repository and host paths

| Previous Gitea reference | Current Forgejo reference |
| --- | --- |
| `ansible/playbooks/02-gitea.yml` | [`ansible/playbooks/02-forgejo.yml`](../../ansible/playbooks/02-forgejo.yml) |
| `ansible/playbooks/03-gitea-runner.yml` | [`ansible/playbooks/03-forgejo-runner.yml`](../../ansible/playbooks/03-forgejo-runner.yml) |
| `compose/gitea/` | [`compose/forgejo/`](../../compose/forgejo/) |
| `compose/gitea-runner/` | [`compose/forgejo-runner/`](../../compose/forgejo-runner/) |
| `images/gitea-runner/Dockerfile` | [`images/forgejo-runner/Dockerfile`](../../images/forgejo-runner/Dockerfile) |
| `.gitea/workflows/platform-ci.yml` | [`.forgejo/workflows/platform-ci.yml`](../../.forgejo/workflows/platform-ci.yml) |
| `scripts/ops/link-gitea-package.sh` | [`scripts/ops/link-forgejo-package.sh`](../../scripts/ops/link-forgejo-package.sh), using `FORGEJO_TOKEN` |
| Git remote `gitea` | Git remote `forgejo`, fetch-only |
| `/srv/storage/state/services/gitea` | `/srv/storage/state/services/forgejo`, fresh application state |
| `/srv/storage/state/services/gitea-runner/.runner` | `/srv/storage/state/services/forgejo-runner/runner.yml`, fresh UUID/token |
| `/etc/systemd/system/gitea.service` | `/etc/systemd/system/forgejo.service` |
| `/etc/systemd/system/gitea-runner.service` | `/etc/systemd/system/forgejo-runner.service` |
| `/usr/local/sbin/gitea-check-storage` | `/usr/local/sbin/forgejo-check-storage` |
| `/usr/local/sbin/gitea-runner-check-storage` | `/usr/local/sbin/forgejo-runner-check-storage` |

These are destination mappings, not filesystem rename instructions. The new host-state directories are separate from the legacy state retained for rollback. The validation runner retains UID/GID 10001, its restricted permissions and no production Docker socket.

The rootful Forgejo installer still uses `/data/gitea/gitea.db` internally. With this repository's `/data` bind, that is `/srv/storage/state/services/forgejo/gitea/gitea.db` on the host. The internal `gitea` component does not refer to the old host-state directory. Keep the configured internal database/config paths; renaming them for branding can disconnect the application from its state.

## Update consumers after transfer

After the private mirror exists and has synchronized, configure its fetch-only remote:

```bash
cd /srv/platform
forgejo_url=http://forgejo.lab.home.arpa:3002/ctalaveraw/arm-homelab-platform.git
if git remote get-url forgejo >/dev/null 2>&1; then
  git remote set-url forgejo "$forgejo_url"
else
  git remote add forgejo "$forgejo_url"
fi
git remote set-url --push forgejo DISABLED
bash scripts/ops/check-source-parity.sh github forgejo
```

Retain the legacy `gitea` remote while rollback is needed. After port cutover, set the `forgejo` fetch URL to the final URL from the table and repeat parity and clone checks. GitHub remains the normal push destination. A checkout whose canonical remote is named `origin` should pass `origin forgejo` to the helper instead.

Update Uptime Kuma's monitor name and URL, bookmarks, Git credential entries, SSH clone URLs/verified host keys, hooks, deploy keys and integrations to the new endpoint and owner. Log Skopeo/OCI clients into the new registry address with a new Forgejo credential; registry auth entries are keyed by hostname and port. Update local registry image prefixes while preserving the qualified digest. Verify package association with `scripts/ops/link-forgejo-package.sh` using owner `ctalaveraw`.

The runner registration remains `http://forgejo:3000/` internally after host-port cutover. Public GitHub URLs, GHCR images, Kubernetes digest references and Flux sources keep their existing canonical identities.

## Intentional legacy references

The repository reference crawl covers tracked paths and all tracked text, including workflows, dotfiles, deployment code, scripts, tests, documentation and evidence captions. Remaining Gitea references have explicit purposes:

| Reference | Reason to retain it |
| --- | --- |
| Legacy state, units, guards and `compose/gitea*` in the migration runbook | Required to stop, retain and recover the old instance; the local Compose directories remain ignored |
| `docs/sprints/02-gitea.md`, `07-native-gitea-ci.md`, dated incidents, benchmark and evidence records | Original results were measured on Gitea; each affected historical record links here for current paths |
| Gitea screenshot filenames and captions | Preserve original evidence identity and working links |
| Dated ADR implementation notes | Describe the prior implementation; current amendments identify Forgejo replacements |
| `/data/gitea/...` inside the rootful Forgejo image | Application layout inside the new Forgejo bind mount |
| Official `/upgrade/from-gitea/` documentation and Gitea import selector | Correct upstream migration terminology |
| Negative storage assertion in `test_forgejo_ingress.py` | Rejects accidental reuse of the old host-state path |

Historical helper, workflow, image and playbook references are accompanied by links to their current files. Historical completion does not satisfy the remaining [Forgejo acceptance checks](gitea-to-forgejo.md#9-acceptance-and-retention).
