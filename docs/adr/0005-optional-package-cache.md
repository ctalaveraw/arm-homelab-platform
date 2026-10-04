# ADR-0005: Shared APT Cache as an Optional Dependency

Status: Accepted
Recorded: 2026-10-04 (retrospective)

## Context

Repeated ARM64 package downloads may increase CI execution
time and external network dependencies.

APT-Cacher-NG has demonstrated reusable package caching
on the R5C.

## Decision

- Operate a shared, SD-backed APT-Cacher-NG service.
- Keep cache data separate from critical application state.
- Configure future build clients to consume it explicitly.
- Do not make R5C host recovery depend on its own proxy.
- Preserve a documented direct-upstream fallback.
- Retain upstream APT package-signature verification.
- Restrict TCP/3142 to intended client networks.
- Monitor cache availability and capacity.

An initial 5 GiB usage-alert threshold is proposed,
but is not an enforced quota or a completed alert.

## Consequences

Repeated package downloads can reuse locally cached data.

Cache failure must not prevent management-host recovery.

APT-Cacher-NG is complementary to BuildKit caching,
prebuilt runners and higher-level artifact repositories.

Measured individual-package improvements must not be
represented as whole-pipeline performance improvements.

Source ACL verification and a complete pipeline-level
benchmark remain outstanding.
