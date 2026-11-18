# CI, mirroring and OCI distribution

GitHub is canonical. The Forgejo pull mirror provides local ARM64 validation and an OCI registry under owner `ctalaveraw`. Source parity, package retrieval and manual/push-triggered native validation passed on 2026-11-18.

## Source ownership

The controller's canonical remote is `github`. Its verified SSH alias `forgejo` resolves to `forgejo.lab.home.arpa:2223`.

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

Other checkouts can use the full SSH URL or `http://git.lab.home.arpa:3000/ctalaveraw/arm-homelab-platform.git`. Pass `origin forgejo` to the helper if the canonical remote is named `origin`.

The helper compares local, GitHub and Forgejo `main`. A recent GitHub change can precede the next mirror sync; synchronize the mirror and repeat the check when that happens. See the [client reference](runbooks/forgejo-reference-map.md).

## Workflows and authority

| Workflow | Worker | Work |
| --- | --- | --- |
| `.github/workflows/platform-ci.yml` | GitHub-hosted ARM64 | Source validation, private Caddy validation, runner image build/smoke check, application build/test/scan and publication |
| `.forgejo/workflows/platform-ci.yml` | Repository-scoped Forgejo Runner | Trusted `main` push and manual repository validation |
| `.github/workflows/controller-public-ingress.yml` | GitHub-hosted ARM64 | Public proxy, cloudflared and Zulip profile checks with disposable configuration |

The Forgejo runner uses `data.forgejo.org/forgejo/runner:13.1.0` with the validation tools installed. It runs as UID/GID 10001, drops all capabilities, publishes no ports and has no production Docker socket. Host-mode jobs run inside this container and share its files and registration secret, so only trusted workflows belong there.

The SD-backed `runner.yml` has a fresh repository-scoped UUID/token, capacity one, label `r5c-arm64-validation:host`, no cache listener and internal server URL `http://forgejo:3000/`. Keep it mode 0600 and outside Git.

Enable the repository Actions unit under **Settings → Units → Overview → Actions**. Register its runner under **repository Settings → Actions → Runners**. The earlier user-scoped registration was removed.

Native run #1 succeeded manually at commit `eb84e2ec9c` in 2m47s. Run #2 succeeded from a mirrored push at `44d3d82ba9` in 2m32s.

Forgejo uses `actions/checkout@v4` with persisted credentials disabled. `DEFAULT_ACTIONS_URL=https://github.com` resolves shorthand actions against GitHub. Mirroring actions and pinning their commit identities remain planned supply-chain work.

## Validation contract

`bootstrap.sh` installs or updates the repository-local toolchain. `validate.sh` checks shell/Python/YAML syntax, ShellCheck, Ruff, yamllint, GitHub actionlint, regression tests, Ansible syntax and Compose rendering with synthetic values. The local worker needs a Compose client but no Docker daemon.

GitHub separately builds the runner and validates Caddy. Controller ingress CI checks unpublished ports, exact proxy trust, storage and secret handling, then initializes Zulip with disposable credentials and waits for its health check. It does not authenticate a real tunnel or send SMTP mail.

The ingress fixture applies the playbook's file and directory preparation tasks to an
isolated path, including root ownership and private parent directories. It starts
with a root-owned mode 0700 application data mount so preparation must repair its
traversal permissions before the image can initialize as the `zulip` user.
It also starts with a checkout-owned mode 0600 public `Caddyfile`; preparation
must make it readable before the pinned Caddy container validates it with all
capabilities dropped.

## Build once and publish

The application passes through these steps:

1. Dockerfile check and ARM64 build.
2. HTTP, architecture and non-root runtime checks on the built image.
3. Trivy vulnerability and secret scan.
4. Image export with checksum and Docker image ID.
5. Isolated publisher job verifies the transfer and loaded image.
6. GHCR publication with `packages: write`.

PR jobs cannot publish. Publication runs only for a push to GitHub `main`. Commit tags identify the source revision; the registry digest identifies the deployed artifact. Flux reads GitHub desired state and remains the application reconciler.

## Local OCI distribution

The transferred `platform-hello` artifact has tag `1ddd76c14a35f974d06dbd1ed7e3c4c14475c92d` and digest:

```text
sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e
```

Its original GHCR/Gitea manifest identity was preserved when copied into Forgejo. Complete retrieval from `git.lab.home.arpa:3000/ctalaveraw/platform-hello` passed, and the package is linked to the mirrored repository.

| Helper | Operation |
| --- | --- |
| `replicate-oci-image.sh` | Copy existing content with `--preserve-digests`; optional source/destination authfiles |
| `verify-oci-parity.sh` | Compare registry manifest digests |
| `verify-oci-retrieval.sh` | Retrieve the artifact into a fresh temporary OCI layout |
| `link-forgejo-package.sh` | Associate a package with a repository using `FORGEJO_TOKEN` |

The current registry uses trusted LAN HTTP. Skopeo needs `DEST_TLS_VERIFY=false` for destination operations and `TLS_VERIFY=false` for retrieval. Keep TLS verification enabled for GHCR and HTTPS endpoints. Authfile entries use the registry hostname and port; log in again after either changes.

Package association and account permissions are separate from content transfer. Kubernetes continues to use GHCR digests.

## Acceptance and records

Kuma's Forgejo monitor targets `http://git.lab.home.arpa:3000/api/healthz`. Expect HTTP 200 and JSON `status: pass`. Notification delivery is a separate check.

The [migration record](runbooks/gitea-to-forgejo.md) contains backup, transfer, cutover and rollback details. Historical results remain in [native Gitea CI](sprints/07-native-gitea-ci.md), [dual OCI distribution](sprints/09-dual-oci-distribution.md) and the [evidence ledger](interview/engineering-evidence.md).
