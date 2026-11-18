# Forgejo names, paths and client URLs

Current LAN configuration, reviewed 2026-11-18.

## Service and account identity

GitHub remains canonical at `https://github.com/ctalaveraw/arm-homelab-platform`. The controller checkout is `/srv/platform`, with canonical remote `github` and fetch-only remote `forgejo`.

Forgejo owner and administrator: **`ctalaveraw`**. The old Gitea account was `admin`; Forgejo reserves that username. Both LAN DNS names resolve to controller IPv4 `10.0.0.50`.

| Setting or client | Current value |
| --- | --- |
| `FORGEJO_FQDN` | `git.lab.home.arpa` |
| `FORGEJO_ROOT_URL` | `http://git.lab.home.arpa:3000/` |
| `FORGEJO_BIND_IP` / `FORGEJO_SSH_BIND_IP` | `10.0.0.50` |
| `FORGEJO_HTTP_PORT` | `3000` |
| `FORGEJO_SSH_PORT` | `2223` |
| HTTP clone | `http://git.lab.home.arpa:3000/ctalaveraw/arm-homelab-platform.git` |
| SSH clone | `ssh://git@git.lab.home.arpa:2223/ctalaveraw/arm-homelab-platform.git` |
| Controller SSH alias | `forgejo` → `forgejo.lab.home.arpa:2223` |
| OCI image | `git.lab.home.arpa:3000/ctalaveraw/platform-hello` |
| Package association | `ctalaveraw/platform-hello` → `ctalaveraw/arm-homelab-platform` |
| Runner internal URL | `http://forgejo:3000/` |
| Kuma target | `http://git.lab.home.arpa:3000/api/healthz` |

The checked-in Forgejo example now uses HTTP/3000. The earlier `forgejo.lab.home.arpa:3002` endpoint was only for parallel migration. Port 3001 belongs to Kuma.

Forgejo is limited to LAN/WireGuard access and has no public tunnel route. Private HTTPS is optional follow-up work; public Zulip uses a separate profile.

## Repository and host paths

| Earlier Gitea path | Current Forgejo path |
| --- | --- |
| `ansible/playbooks/02-gitea.yml` | [`02-forgejo.yml`](../../ansible/playbooks/02-forgejo.yml) |
| `ansible/playbooks/03-gitea-runner.yml` | [`03-forgejo-runner.yml`](../../ansible/playbooks/03-forgejo-runner.yml) |
| `compose/gitea/` | [`compose/forgejo/`](../../compose/forgejo/) |
| `compose/gitea-runner/` | [`compose/forgejo-runner/`](../../compose/forgejo-runner/) |
| `images/gitea-runner/Dockerfile` | [`images/forgejo-runner/Dockerfile`](../../images/forgejo-runner/Dockerfile) |
| `.gitea/workflows/platform-ci.yml` | [`.forgejo/workflows/platform-ci.yml`](../../.forgejo/workflows/platform-ci.yml) |
| `scripts/ops/link-gitea-package.sh` | [`link-forgejo-package.sh`](../../scripts/ops/link-forgejo-package.sh), using `FORGEJO_TOKEN` |
| Git remote `gitea` | Fetch-only remote `forgejo` |
| `/srv/storage/state/services/gitea` | `/srv/storage/state/services/forgejo` |
| `/srv/storage/state/services/gitea-runner/.runner` | `/srv/storage/state/services/forgejo-runner/runner.yml` |
| `/etc/systemd/system/gitea.service` | `/etc/systemd/system/forgejo.service` |
| `/etc/systemd/system/gitea-runner.service` | `/etc/systemd/system/forgejo-runner.service` |
| `/usr/local/sbin/gitea-check-storage` | `/usr/local/sbin/forgejo-check-storage` |
| `/usr/local/sbin/gitea-runner-check-storage` | `/usr/local/sbin/forgejo-runner-check-storage` |

The destination state was created separately. The retained Gitea directories are rollback material, not rename sources. Forgejo Runner uses UID/GID 10001 and its own UUID/token.

The rootful Forgejo image still uses `/data/gitea/gitea.db` internally. With the new `/data` bind, its host path is `/srv/storage/state/services/forgejo/gitea/gitea.db`. Keep that internal layout.

## Update consumers after transfer

The controller SSH alias and host key were verified during migration. Configure its fetch-only remote:

```bash
cd /srv/platform
forgejo_url=ssh://git@forgejo/ctalaveraw/arm-homelab-platform.git
if git remote get-url forgejo >/dev/null 2>&1; then
  git remote set-url forgejo "$forgejo_url"
else
  git remote add forgejo "$forgejo_url"
fi
git remote set-url --push forgejo DISABLED
bash scripts/ops/check-source-parity.sh github forgejo
```

Run parity from an updated `main` checkout after the mirror has synchronized. Pass `origin forgejo` if needed. An old Gitea HTTP/3000 URL now reaches Forgejo on the same controller; legacy SSH/2222 is stopped.

Registry authentication uses the hostname and port. To verify the transferred artifact again:

```bash
skopeo login --tls-verify=false --username ctalaveraw \
  --authfile "$HOME/.config/containers/forgejo-auth.json" git.lab.home.arpa:3000
AUTHFILE="$HOME/.config/containers/forgejo-auth.json" TLS_VERIFY=false \
  bash scripts/ops/verify-oci-retrieval.sh \
  docker://git.lab.home.arpa:3000/ctalaveraw/platform-hello@sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e
```

The TLS flag permits this trusted LAN HTTP registry. Keep verification enabled for GHCR and HTTPS. Git parity and full retrieval have already passed; routine documentation updates do not require re-copying or re-linking the package.

Kuma now targets `/api/healthz`; expect HTTP 200 with JSON `status: pass`. The Actions page records successful manual and push-triggered runs. Keep generated clone/package URLs and any integrations aligned with the current table.

GitHub URLs, GHCR images, Kubernetes digests, Flux sources and the runner's internal server URL are unchanged.

## Intentional legacy references

| Reference | Why it remains |
| --- | --- |
| Retained Gitea state, units, guards and ignored `compose/gitea*` directories | Needed for rollback |
| Dated Gitea sprint, incident, benchmark and evidence records | Names and measurements describe the original deployment |
| Screenshot filenames | Identify the original evidence |
| Historical ADR context | Records the reason for a decision |
| `/data/gitea/...` in the rootful Forgejo image | Upstream internal layout |
| Official `/upgrade/from-gitea/` documentation and Gitea import selector | Upstream migration terminology |
| Negative storage assertion in `test_forgejo_ingress.py` | Rejects reuse of legacy host state |

See the [migration checklist](gitea-to-forgejo.md#9-acceptance-and-retention) before deleting retained legacy data.
