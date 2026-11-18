# CI, Mirroring and OCI Distribution

Updated 2026-11-18. Forgejo serves LAN HTTP/3000 and SSH/2223 with an active repository-scoped runner. Git parity, SSH read and full OCI retrieval passed during staging. Post-cutover source parity and OCI retrieval passed; manual and push-triggered native Actions runs are green, and Kuma reports the final root URL Up. Prior Gitea results remain historical evidence.

## Source ownership

GitHub is canonical. Forgejo provides a populated one-way pull mirror under `ctalaveraw/arm-homelab-platform`, intended to be private, with repository-scoped validation. The new runner was deployed and exercised by a native workflow. Do not push routine changes to both forges. GitHub remains available for controller recovery when the local forge is unavailable.

After the mirror has synchronized, configure a fetch-only `forgejo` remote using the controller's verified SSH alias (hostname `forgejo.lab.home.arpa`, port `2223`):

```bash
forgejo_url=ssh://git@forgejo/ctalaveraw/arm-homelab-platform.git
if git remote get-url forgejo >/dev/null 2>&1; then
  git remote set-url forgejo "$forgejo_url"
else
  git remote add forgejo "$forgejo_url"
fi
git remote set-url --push forgejo DISABLED
bash scripts/ops/check-source-parity.sh github forgejo
```

The controller's canonical remote is `github`; another checkout may pass `origin` explicitly. The current HTTP alternative is `http://git.lab.home.arpa:3000/ctalaveraw/arm-homelab-platform.git`. See the [reference map](runbooks/forgejo-reference-map.md) for other SSH/registry URLs. The parity helper compares local `main`, canonical GitHub `main` and the mirrored branch. A pending mirror synchronization may legitimately cause temporary divergence; do not force-push either side to conceal it.

## Workflows and authority

| Workflow | Engine | Purpose |
| --- | --- | --- |
| `.github/workflows/platform-ci.yml` | GitHub-hosted ARM64 | Repository checks, Caddy validation, runner build/smoke test, application build/test/scan and narrowly scoped publication |
| `.forgejo/workflows/platform-ci.yml` | Local Forgejo Runner | Trusted `main` and manual repository validation |

The Forgejo runner image uses `data.forgejo.org/forgejo/runner:13.1.0` plus repository validation tools. It runs as UID/GID 10001, drops all capabilities, publishes no ports and receives no production Docker socket. Host-mode jobs execute inside this runner container and share its files and registration secret; this is a trusted worker, not isolation for untrusted PR code.

Use a fresh repository-scoped Forgejo UUID/token in the SD-backed `runner.yml`. Do not reuse Gitea runner state. The checked-in example sets capacity one, the `r5c-arm64-validation:host` label, an internal Forgejo URL and no cache listener. Keep the real file mode 0600 and outside Git.

Forgejo uses `actions/checkout@v4`, with `persist-credentials: false`. `DEFAULT_ACTIONS_URL` explicitly resolves shorthand actions against GitHub, preserving the current dependency. Owning/mirroring upstream actions and pinning their commit identities remains separate supply-chain work; switching forge software alone does not accomplish that.

Enable the repository's Actions unit under **Settings → Units → Overview → Actions**; registering a runner alone does not add the tab. The active registration is repository-scoped, and the earlier user-scoped registration was removed. The Actions page records successful native run #1 (manual, commit `eb84e2ec9c`, 2m47s) and run #2 (push, commit `44d3d82ba9`, 2m32s). The push-triggered run on the pull mirror establishes this behavior for the observed synchronization; it does not promise every future event or branch will run.

## Validation contract

`bootstrap.sh` converges the pinned Python toolchain. `validate.sh` performs tracked shell/Python/YAML checks, ShellCheck, Ruff, yamllint, GitHub actionlint, regression tests, Ansible syntax and synthetic Compose rendering. It does not print production secrets or require a Docker daemon in the local validation worker.

Caddyfile validation and the runner container build execute separately on GitHub-hosted ARM64, which has Docker. These checks cannot validate home routes, certificate issuance, SD hardware or imported application data.

## Build once and publish

The application pipeline carries one Linux ARM64 image through:

1. Dockerfile check and build.
2. HTTP, architecture and non-root runtime acceptance.
3. Trivy vulnerability and secret scan.
4. Image export, archive checksum and recorded Docker image ID.
5. Separate-job transfer, checksum validation and loaded image-ID comparison.
6. Publication to GHCR from a job with `packages: write`.

PRs validate/build/test/scan but cannot publish. Commit-derived tags provide traceability; the registry digest is the deployment identity. Flux remains the routine application reconciler.

Historical qualified artifact:

```text
ghcr.io/ctalaveraw/platform-hello@sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e
```

This digest was measured before the Forgejo migration. Later promotions must use their independently captured digest.

## Local OCI distribution

The repository-owned helpers remain registry-independent except for the Forgejo package link:

- `replicate-oci-image.sh`: Skopeo copy with `--preserve-digests`; separate optional source/destination authfiles.
- `verify-oci-parity.sh`: compare source and destination registry manifest digests.
- `verify-oci-retrieval.sh`: retrieve the complete artifact into a fresh temporary OCI layout.
- `link-forgejo-package.sh`: associate an existing package with the intended mirrored repository using `FORGEJO_TOKEN`.

Use normal TLS verification for HTTPS. `DEST_TLS_VERIFY=false` and `TLS_VERIFY=false` are needed only for the trusted LAN HTTP registry, including the current TCP/3000 endpoint. Keep normal verification enabled for GHCR and any future HTTPS endpoint.

The existing `platform-hello` artifact was copied from Gitea without rebuilding and associated with the Forgejo repository. Staging source/destination digest parity and complete retrieval passed for the qualified digest above, retaining tag `1ddd76c14a35f974d06dbd1ed7e3c4c14475c92d`. Repeat retrieval using the final registry address after updating its authfile entry. Package association, credentials and ownership are separate from Skopeo's content transfer. Existing Kubernetes GHCR references remain unchanged.

Use destination `git.lab.home.arpa:3000/ctalaveraw/platform-hello`. The earlier `forgejo.lab.home.arpa:3002` address was the staging registry, and old source owner `admin` is reserved in Forgejo. Re-authenticate OCI clients at the new hostname and port. LAN HTTP still needs the explicit local-only TLS flags until private HTTPS is deployed.

## Acceptance and records

Follow [migration and rollback](runbooks/gitea-to-forgejo.md) and [domain ingress](runbooks/domain-ingress.md). The reusable endpoint commands are in the [reference map](runbooks/forgejo-reference-map.md#update-consumers-after-transfer). Kuma currently reports `http://git.lab.home.arpa:3000/` Up. Prefer `http://git.lab.home.arpa:3000/api/healthz` for application health, expecting HTTP 200 with JSON `status: pass`; notification delivery is a separate check. Historical proof remains in [native Gitea CI](sprints/07-native-gitea-ci.md), [dual distribution](sprints/09-dual-oci-distribution.md) and the [engineering evidence ledger](interview/engineering-evidence.md).

## Controller tunnel validation

The dedicated controller public-ingress workflow validates the pinned Caddy and
cloudflared images on ARM64 without authenticating a real tunnel. It renders
only synthetic settings and a deliberately invalid CI file-secret fixture,
checks the token-file CLI, and runs a loopback-only proxy smoke test.
Regression tests protect unpublished ports, exact proxy trust, private Forgejo
isolation, canonical SD credentials and non-echoing atomic token installation.
The colocated overlay is rendered together with the base ingress manifest and
checked against the runtime storage/network contract. ARM64 CI initializes the
official Zulip image with disposable file credentials, starts the application
and dependencies, and waits for the inherited application health check. It does
not start an authenticated Cloudflare connection or send actual SMTP mail.
Tests also cover exact Caddy-to-Zulip trust, memory/swap/storage minimums and
preservation of the complete application credential set on reinitialization.
No real deployment configuration, diagnostics or credentials are CI inputs.
