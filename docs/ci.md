# CI, repository mirroring, and application acceptance

**Status (2026-10-04):** Dual ARM64 repository validation is operational. GitHub Actions also builds and runtime-tests the first application. Image scanning, publication, and Kubernetes delivery remain pending.

## Source ownership

- **GitHub:** public canonical source, hosted CI, and off-device recovery copy.
- **Gitea:** private native one-way pull mirror of GitHub.
- The management plane must remain reconstructable without depending on Gitea.
- Git mirroring synchronizes Git refs/history; it does not copy GitHub Actions run history, repository secrets, or OCI artifacts.

A forced Gitea mirror synchronization was observed to emit a `push` event on `main`, triggering the native Gitea Actions workflow.

## Portable repository validation

Repository-owned entrypoints:

```bash
bash scripts/ci/bootstrap.sh
bash scripts/ci/validate.sh
```

`bootstrap.sh` creates the ignored `.ci-venv/`, installs pinned Ansible Core 2.21.4 plus PyYAML, and ensures hosted CI has ShellCheck.

`validate.sh` currently checks:

- Bash syntax;
- ShellCheck;
- Python storage-guard syntax;
- YAML parsing;
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

The checkout action was upgraded from v4 to v5 to remove the GitHub-hosted Node.js 20 deprecation warning.

### build-hello

`build-hello` declares:

```yaml
needs: validate
```

Therefore the application build does not run if repository/Dockerfile validation fails.

It checks out a fresh copy of committed source and executes:

```bash
bash scripts/ci/test-hello.sh
```

The script:

- builds a Linux ARM64 image;
- confirms image architecture;
- verifies runtime UID 10001;
- starts a temporary container;
- polls HTTP readiness;
- verifies expected page content;
- captures logs on failure;
- cleans up the temporary container.

Current limitation: `test-hello.sh` still performs the image build itself. Before scan/publication, the pipeline will be refactored to build one explicit image once, then test, scan, and publish that same artifact.

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

The runner currently performs repository validation only. It intentionally does not build/publish application images because the trusted validation worker has not been granted a production Docker socket or registry credentials.

Gitea remains on `actions/checkout@v4` until newer action-runtime compatibility is explicitly tested.

## Fail-fast behavior

CI depends on process exit status, not log wording.

- exit status `0`: success;
- nonzero exit status: failure;
- stdout/stderr provide operator diagnostics but do not independently control job state;
- `needs: validate` prevents downstream image work when validation fails.

A stale local Docker image must never be accepted as proof of a current successful build.

## Planned artifact contract

The publication path will enforce:

```text
build image A
  -> test image A
  -> scan image A
  -> publish image A
  -> record digest of image A
  -> replicate image A
  -> deploy image A by immutable identity
```

An independent rebuild after testing is intentionally avoided.

## Mirror operations

Canonical GitHub main:

```bash
git ls-remote https://github.com/ctalaveraw/arm-homelab-platform.git refs/heads/main
```

Compare the full SHA to the mirrored Gitea `main` reference and its synchronization timestamp. Use **Synchronize Now** when immediate pull synchronization is required.

## Evidence

- [CI foundation sprint](sprints/06-ci-foundation.md)
- [Native Gitea CI sprint](sprints/07-native-gitea-ci.md)
- [Application delivery sprint](sprints/08-application-delivery-foundation.md)
- [Engineering evidence ledger](interview/engineering-evidence.md)
- [PLAT-006 screenshots](evidence/plat-006/)
