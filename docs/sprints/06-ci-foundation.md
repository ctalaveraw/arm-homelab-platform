# Sprint 6 — Portable ARM64 CI and Gitea mirror

Date: 2026-10-04
Status: GitHub CI complete; Gitea runner not yet deployed.

## Decision

The workflows are platform adapters. The actual validation logic is
repository-owned in `scripts/ci/bootstrap.sh` and `scripts/ci/validate.sh`.
Future Gitea Actions jobs should invoke those same scripts.

## Implemented

- Added `.github/workflows/platform-ci.yml` on an ARM64 hosted runner.
- Bootstrapped pinned Ansible Core and PyYAML and ran ShellCheck in CI.
- Validated Python guards, YAML, all six Ansible playbooks, and all four
  Compose manifests using synthetic, non-secret variables.
- Added three regression tests for the stateful Compose safety contract.
- Created a private native Gitea pull mirror of canonical public GitHub.

## Evidence

Three consecutive GitHub workflow runs succeeded:

- Run #1: commit `a5d3222`, initial portable CI.
- Run #2: commit `3cddc6d`, common ShellCheck package.
- Run #3: commit `3e58f61`, three Compose contract tests passed.
- [Run #3 job](https://github.com/ctalaveraw/arm-homelab-platform/actions/runs/37186219090)
- Gitea displayed its pull mirror at full `main` SHA
  `3e58f61e8855b41623490c560f90f774b72ca3f0`; GitHub
  `git ls-remote` matched at the time of verification.

## Boundaries and next

Hosted static tests do not recreate the SD automount or execute the
real mount guard. The mirror does not include GitHub's workflow history.
The Gitea runner, HTTPS, OCI publication and cluster delivery remain
future work. Do not turn an unverified state into a checked milestone.

See [portable CI runbook](../ci.md).
