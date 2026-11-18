# ADR-0005: Optional shared APT cache

Status: Accepted
Recorded: 2026-10-04

## Context

The R5C package benchmark demonstrated reusable APT caching. A single-package result does not measure the full dependency-install stage.

## Decision

Run SD-backed APT-Cacher-NG as an optional service. Keep cache data separate from critical application state, retain APT signature verification and restrict TCP/3142 to intended clients.

Configure clients explicitly and document direct-upstream fallback. R5C recovery must work while its own cache is unavailable.

## Implementation and remaining checks

The cache is operational. Source ACL verification and a full pipeline cold/warm benchmark remain open. The proposed 5 GiB usage alert is not an enforced quota or a deployed alert.

Forgejo validation is operational, but cache integration is not required by the CI profile. Test the complete install stage after wiring a controlled client path. BuildKit and prebuilt runner caches address different downloads.

## Evidence

- [Package benchmark](../benchmarks/2026-10-04-apt-cacher-ng.md)
- [CI configuration](../ci.md)
- [Current backlog](../backlog.md)
