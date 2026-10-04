# Portable CI and repository mirroring

Status: GitHub-hosted ARM64 validation operational (2026-10-04).
Gitea runner and delivery pipeline: planned.

## Source ownership

- **GitHub**: public canonical source, CI execution and independent recovery copy.
- **Gitea**: private native **pull mirror** of GitHub, not a second push target.
- Do not make management-plane reconstruction depend on Gitea.
- The first observed mirror synchronization matched `main` at `3e58f61`.
- A Git mirror synchronizes Git references/history; it does not copy GitHub
  Actions runs, repository settings, credentials or artifacts.

## CI boundary

`.github/workflows/platform-ci.yml` owns triggers and runner selection only.
Validation behavior lives in `scripts/ci/`, reused from local shells and
future CI adapters. Do not fork check implementations into workflow YAML.

On an equipped R5C:

```bash
bash scripts/ci/validate.sh
```

On a new development/hosted validation environment:

```bash
bash scripts/ci/bootstrap.sh
bash scripts/ci/validate.sh
```

The bootstrap script creates the ignored `.ci-venv/`, pins Ansible Core,
installs PyYAML, and ensures ShellCheck is present in hosted CI.
Validation discovers Git-tracked files, not the untracked OpenBao draft.
Compose rendering uses synthetic variables and `--env-file /dev/null`,
not the populated host-specific `.env` files.

## Currently enforced

- Bash syntax and ShellCheck when available (required in hosted CI)
- Python storage-guard parsing and YAML parsing
- Ansible playbook syntax for 00 through 05
- Rendered Compose configuration checks
- Three static regression tests: guarded restart policy; exact state bind
  and `create_host_path: false`; explicit bind-address variables

These checks do not execute SD guard scripts on a hosted runner.
They do not demonstrate full-host recovery, runtime authorization, image
build/scan, registry push or Kubernetes delivery.

## Mirror verification and operations

GitHub's canonical main reference:

```bash
git ls-remote https://github.com/ctalaveraw/arm-homelab-platform.git refs/heads/main
```

Compare that full SHA with Gitea's displayed `main` commit and inspect
its mirror synchronization timestamp. Use **Synchronize Now** in Gitea
mirror settings when an immediate pull is needed. Observe that pull
mirroring is periodic, so propagation is not necessarily instantaneous.

Do not enable an arbitrary Gitea Actions runner or copy secrets into the
mirror just to match GitHub CI. Runner labels, isolation and permissions
need explicit design first.

## Published proof

- [GitHub Actions run #3: contract tests passed](https://github.com/ctalaveraw/arm-homelab-platform/actions/runs/37186219090)
- [Engineering evidence ledger](interview/engineering-evidence.md)
- [CI foundation sprint](sprints/06-ci-foundation.md)
