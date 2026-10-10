# ADR-0011: Independent encrypted recovery root and explicit configuration classes

Status: Accepted for target architecture
Date: 2026-10-10

## Context

The existing R5C Ansible preflight assumes ARM64, a working OS, Python, Git and an ext4 SD automount with expected filesystem label. This is convergence of a running host, **not** day-zero provisioning. Runtime `.env` files, local service keys, Gitea state, runner identity, deployer X.509 material, signing trust and eventual OpenBao credentials cannot be assumed recoverable from public Git.

## Decision

Use an encrypted, versioned **off-device recovery bundle** and independent custodian-accessible decryption path for bootstrap secrets and reconstructive instructions. OpenBao, once installed, serves **routine** dynamic/short-lived secret delivery, not the sole recovery root for its own unseal/rebuild or host/bootstrap identity.

Separate four configuration classes:
1. Public declarative configuration (Git).
2. Non-secret site-specific configuration (inventory/structured config, with examples and validation).
3. Runtime secrets (restricted host-owned files or supported secure injection, eventually OpenBao).
4. Recovery/issuer keys and bootstrap material (encrypted off-device bundle, independently recoverable, least exposure).

Tracked `.env.example` files are examples/schema only; real `.env` files remain ignored and tightly permissioned. Prefer app-supported file injection for secrets when feasible; avoid secret interpolation in logs, verbose shell tracing, command lines and CI artifacts. Define key owners, expiry and rotation, audit, encryption key escrow, restore sequence, and backup of config *and* persistent state. Never commit raw private keys, admin kubeconfigs, vault recovery shares, tokens or populated `.env` files.

Use a staged recovery chain: acquire supported replacement hardware or VM → establish bootable OS, network, trust, storage and mount guards → install runner/Ansible prerequisites → restore/reissue secrets from independent root → converge systemd/Compose/Gitea/services → validate identity and package states → recover cluster bootstrap/etcd when in incident scope → restore routine secret service.

RTO 4h and RPO 1h are **targets**, subject to classification, destinations, key access, hourly-enough consistent backup, spare hardware and timed isolated drills. Do not claim attainment before multiple rehearsals. In particular, a snapshot cadence does not alone prove recoverable RPO.

## Consequences

The recovery bundle becomes a critical protected asset and must itself have redundant trusted access, verified integrity, access logging and revocation/rotation procedure. Stronger independence adds operational ceremony but removes circular dependence on Gitea, OpenBao or a live R5C.

## Implementation evidence required

Blank-device/bootstrap drill, missing/compromised certificate scenario, secrets restore without local vault, Gitea/OCI consistency and backup validation, etcd/rebuild boundary, changed filesystem label/wrong device negative test, measured RTO/RPO with incident timestamps and declared losses.
