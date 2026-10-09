# CI, repository mirroring, and OCI publication

**Status (2026-10-09):** Dual ARM64 repository validation is operational. GitHub Actions builds one ARM64 application image, runtime-tests and Trivy-scans that exact image, transfers it across an isolated job boundary with integrity verification, and publishes it to GHCR from a narrowly scoped publisher job. The qualified artifact is independently retrievable from GHCR and Gitea with matching registry manifest digests, deployed to Kubernetes by immutable digest, and proven through controlled rollout failure and rollback.

## Source ownership

- **GitHub:** public canonical source, hosted CI, protected `main`, and off-device recovery copy.
- **Gitea:** private native one-way pull mirror of GitHub.
- The management plane must remain reconstructable without depending on Gitea.
- Git mirroring synchronizes Git refs/history; it does not copy GitHub Actions run history, repository secrets, or OCI artifacts.

A forced Gitea mirror synchronization was observed to emit a `push` event on `main`, triggering the native Gitea Actions workflow.

The R5C working copy also keeps Gitea as a **fetch-only** remote. `scripts/ops/check-source-parity.sh` fetches GitHub and Gitea and compares:

- controller-local `main`;
- canonical GitHub `main`;
- mirrored Gitea `main`.

The script does not treat Gitea as a second push target.

## Portable repository validation

Repository-owned entrypoints:

```bash
bash scripts/ci/bootstrap.sh
bash scripts/ci/validate.sh
```

`bootstrap.sh` creates or reuses the ignored `.ci-venv/` and converges pinned validation dependencies on every run rather than assuming an existing venv is current.

Current pinned Python-side tooling includes:

- `ansible-core==2.21.4`;
- `PyYAML>=6,<7`;
- Ruff;
- yamllint;
- actionlint-py.

Hosted CI also ensures ShellCheck is available.

`validate.sh` currently checks:

- Bash syntax;
- ShellCheck;
- Python storage-guard syntax;
- Ruff across tracked Python;
- YAML parsing;
- yamllint using `.yamllint.yml`;
- actionlint for GitHub Actions workflows;
- four Compose safety-contract unit tests;
- Ansible syntax for playbooks `00` through `06`;
- rendered configuration for five Compose projects using synthetic, non-secret values.

The four Compose contract tests enforce:

1. Docker restart policy cannot bypass systemd lifecycle ownership.
2. Stateful storage uses the expected explicit bind and `create_host_path: false`.
3. Network-facing services require explicit host bind addresses while the runner publishes no ports.
4. The Gitea runner remains non-root/minimally privileged and has no host Docker socket.

Hosted tests do not emulate the physical SD filesystem, so they complement rather than replace real mount-guard tests.

## GitHub Actions

Workflow: `.github/workflows/platform-ci.yml`

### validate

Runs on GitHub-hosted `ubuntu-24.04-arm` and performs:

1. `actions/checkout@v5` with persisted credentials disabled;
2. CI dependency bootstrap;
3. portable repository validation;
4. Buildx `--check` against `apps/platform-hello/Dockerfile`.

### build-hello

`build-hello` declares:

```yaml
needs: validate
```

and retains:

```yaml
permissions:
  contents: read
```

The job creates one commit-associated image reference:

```text
platform-hello:<github.sha>
```

The repository-owned stages are:

```bash
bash scripts/ci/build-hello.sh "$IMAGE_REF"
bash scripts/ci/test-hello.sh "$IMAGE_REF"
bash scripts/ci/scan-hello.sh "$IMAGE_REF"
```

The test stage verifies:

- `linux/arm64`;
- runtime UID 10001;
- HTTP readiness;
- expected application content.

The scan stage performs:

- vulnerability scanning;
- secret scanning;
- visibility for UNKNOWN/LOW/MEDIUM/HIGH/CRITICAL findings;
- promotion failure on CRITICAL findings.

The same image is not rebuilt between build, test and scan.

### Image export and job handoff

Only trusted `push` events on `main` export the tested/scanned image.

`scripts/ci/export-image.sh` records:

- the Docker image ID;
- a `docker save` archive;
- SHA-256 for the archive.

The archive is uploaded as a short-retention GitHub Actions artifact.

An early post-merge run exposed that hidden `.ci-artifacts/` paths are excluded by default by `actions/upload-artifact`. The transfer directory was changed to visible `ci-artifacts/`; the fix was verified in the next post-merge run.

### publish-hello

The separate publisher job depends on `build-hello` and runs only on trusted pushes to `main`.

Its permissions are intentionally narrower than a monolithic build/publish job:

```yaml
permissions:
  contents: read
  packages: write
```

The publisher:

1. checks out only the repository scripts it needs;
2. downloads the exported image;
3. verifies the archive checksum;
4. loads the image;
5. verifies the loaded Docker image ID equals the ID recorded before transfer;
6. authenticates to GHCR with the automatically supplied `GITHUB_TOKEN`;
7. calls `scripts/ci/publish-image.sh`;
8. logs out of GHCR.

No PAT or manually injected registry password is required for the current GitHub-to-GHCR path.

## First verified GHCR publication

GitHub Actions run #27 successfully completed all three jobs:

```text
validate
  -> build/test/scan/export/upload
  -> download/verify/authenticate/publish/logout
```

Source commit:

```text
1ddd76c14a35f974d06dbd1ed7e3c4c14475c92d
```

Docker image ID before and after transfer:

```text
sha256:6778f34a5be85bfd970f9124f53efb761d12317feb15c0a4f5c2b29117a0416b
```

Published tag:

```text
ghcr.io/ctalaveraw/platform-hello:1ddd76c14a35f974d06dbd1ed7e3c4c14475c92d
```

GHCR registry digest:

```text
sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e
```

The commit-derived tag is traceable but movable. The registry digest is the immutable identity intended for retrieval and deployment.

## Dual OCI distribution

PLAT-008 extends the qualified artifact from GHCR into the local Gitea container registry without rebuilding it.

Skopeo 1.18.0 is installed declaratively through the R5C Ansible common-package baseline.

The source artifact is:

```text
ghcr.io/ctalaveraw/platform-hello@sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e
```

The Gitea destination repository is:

```text
gitea.lab.home.arpa:3000/admin/platform-hello
```

The promotion path is:

```text
qualified GHCR digest
  -> skopeo copy --preserve-digests
  -> Gitea OCI
  -> compare registry manifest digests
  -> retrieve complete artifact from both registries
  -> link Gitea package to mirrored source repository
```

Both registries report the same registry manifest digest:

```text
sha256:f3c542d3bbc8599f83019263899c2396f6f7aadbda781f329d5a0fa17afaa61e
```

Repository-owned operational scripts are:

- `scripts/ops/replicate-oci-image.sh`;
- `scripts/ops/verify-oci-parity.sh`;
- `scripts/ops/verify-oci-retrieval.sh`;
- `scripts/ops/link-gitea-package.sh`.

Registry and API credentials remain caller-owned and are not embedded in the scripts.

The Gitea package-link helper is desired-state aware:

```text
already linked to requested repository
  -> PASS

unlinked
  -> create association

linked to another repository
  -> fail closed
```

A second registry improves distribution availability, but does not establish off-device backup, build provenance, or artifact safety by itself.

## Gitea Actions

Workflow: `.gitea/workflows/platform-ci.yml`

Runner:

- `r5c-arm64-validation-01`;
- Gitea runner v3.5.0;
- repository-scoped;
- physical NanoPi R5C / ARM64;
- UID/GID 10001;
- host-mode job execution inside a dedicated runner container;
- no privileged mode;
- no host Docker socket;
- no deployment or registry credentials.

The runner intentionally performs repository validation only.

Gitea remains on `actions/checkout@v4` until newer action-runtime compatibility is explicitly tested.

## Fail-fast behavior

CI depends on process exit status, not log wording.

- exit status `0`: success;
- nonzero exit status: failure;
- stdout/stderr provide operator diagnostics but do not independently control job state;
- `needs: validate` prevents downstream image work when validation fails;
- CRITICAL Trivy findings stop promotion;
- missing/altered transfer artifacts stop publication;
- a Docker image-ID mismatch stops publication.

A stale local Docker image must never be accepted as proof of a current successful build.

## Artifact contract

Implemented:

```text
build image A
  -> test image A
  -> scan image A
  -> export image A
  -> verify transferred image A
  -> publish image A
  -> record registry digest
```

Also implemented:

```text
registry digest
  -> independently retrieve from GHCR
  -> replicate same artifact into Gitea OCI
  -> preserve manifest digest
  -> independently retrieve from Gitea
  -> associate package with mirrored repository
```

Also implemented:

```text
known immutable digest
  -> deploy to Kubernetes
  -> verify runtime image identity
  -> inject controlled bad revision
  -> observe failed rollout
  -> preserve serving replica
  -> rollback
  -> reconcile with Git desired state
```

An independent rebuild after testing is intentionally avoided.

## CI action runtime

Both artifact upload and download steps now use the v5 actions used by the
current GitHub-hosted workflow.

## Evidence

- [CI foundation sprint](sprints/06-ci-foundation.md)
- [Native Gitea CI sprint](sprints/07-native-gitea-ci.md)
- [Application delivery sprint](sprints/08-application-delivery-foundation.md)
- [Engineering evidence ledger](interview/engineering-evidence.md)
- [PLAT-006 screenshots](evidence/plat-006/)
- GitHub Actions run #27: `37284420724`
