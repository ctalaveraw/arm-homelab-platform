# CI, Mirroring and OCI Distribution

Updated 2026-11-17. Configuration now targets Forgejo. Prior Gitea runner and registry success remains historical evidence; repeat those checks after migration.

## Source ownership

GitHub is canonical. Forgejo is a private one-way pull mirror with repository-scoped validation. Do not push routine changes to both forges. GitHub remains available for controller recovery when the local forge is unavailable.

The controller keeps a fetch-only `forgejo` remote:

```bash
git remote add forgejo http://forgejo.lab.home.arpa:3002/OWNER/arm-homelab-platform.git
git remote set-url --push forgejo DISABLED
bash scripts/ops/check-source-parity.sh origin forgejo
```

Use the final HTTPS URL after domain acceptance. The parity helper compares local `main`, canonical GitHub `main` and the mirrored branch. A pending mirror synchronization may legitimately cause temporary divergence; do not force-push either side to conceal it.

## Workflows and authority

| Workflow | Engine | Purpose |
| --- | --- | --- |
| `.github/workflows/platform-ci.yml` | GitHub-hosted ARM64 | Repository checks, Caddy validation, runner build/smoke test, application build/test/scan and narrowly scoped publication |
| `.forgejo/workflows/platform-ci.yml` | Local Forgejo Runner | Trusted `main` and manual repository validation |

The Forgejo runner image uses `data.forgejo.org/forgejo/runner:13.1.0` plus repository validation tools. It runs as UID/GID 10001, drops all capabilities, publishes no ports and receives no production Docker socket. Host-mode jobs execute inside this runner container and share its files and registration secret; this is a trusted worker, not isolation for untrusted PR code.

Use a fresh repository-scoped Forgejo UUID/token in the SD-backed `runner.yml`. Do not reuse Gitea runner state. The checked-in example sets capacity one, the `r5c-arm64-validation:host` label, an internal Forgejo URL and no cache listener. Keep the real file mode 0600 and outside Git.

Forgejo uses `actions/checkout@v4`, with `persist-credentials: false`. `DEFAULT_ACTIONS_URL` explicitly resolves shorthand actions against GitHub, preserving the current dependency. Owning/mirroring upstream actions and pinning their commit identities remains separate supply-chain work; switching forge software alone does not accomplish that.

The previous Gitea mirror was observed to emit a push event after forced synchronization. Forgejo's mirror-trigger behavior and a complete validation run must be tested before retiring that runner.

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

Use normal TLS verification for the final domain. `DEST_TLS_VERIFY=false` and `TLS_VERIFY=false` are restricted to the temporary trusted LAN HTTP endpoint during migration. This does not authorize disabling verification for public HTTPS.

Re-publish required OCI artifacts from GHCR or the old registry without rebuilding, then verify parity and full retrieval. Package association, credentials and ownership must be established on Forgejo; they are not transferred by Skopeo. Existing Kubernetes GHCR references remain unchanged.

## Acceptance and records

Follow [migration and rollback](runbooks/gitea-to-forgejo.md) and [domain ingress](runbooks/domain-ingress.md). Update Kuma, OCI clients and the fetch-only remote only after successful checks. Historical proof remains in [native Gitea CI](sprints/07-native-gitea-ci.md), [dual distribution](sprints/09-dual-oci-distribution.md) and the [engineering evidence ledger](interview/engineering-evidence.md).
