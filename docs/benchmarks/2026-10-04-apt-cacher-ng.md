# BENCH-001 — ARM64 APT Package Cache

**Date:** October 4, 2026
**Platform:** NanoPi R5C, Debian Trixie / ARM64
**Service:** APT-Cacher-NG, containerized on Docker
**Classification:** Single-package controlled experiment

## Objective

Determine whether a local package cache can reduce repeated upstream package downloads and retain cached artifacts across container recreation.

## Test configuration

- Proxy endpoint: `10.0.0.50:3142`
- Persistent storage: `/srv/storage/state/services/apt-cacher-ng`
- Backing filesystem: ext4, label `storage_sdcard`
- Test package: `coreutils_9.7-3_arm64.deb`
- Package payload: 2,948,764 bytes
- Two identical requests through the same explicit HTTP proxy

## Measured results

| Measurement | First request | Second request |
|---|---:|---:|
| HTTP status | 200 | 200 |
| Downloaded bytes | 2,948,764 | 2,948,764 |
| Total request time | 199.713 ms | 15.229 ms |
| Package integrity | Passed | Passed |

The second request completed approximately **13.1 times faster**, representing a 92.4% reduction in elapsed time for this particular package retrieval.

Both downloads returned the same SHA-256 checksum:

`99b2531e8d16e4f2d3f239ae3cb57913ec1f43764d2d6cd5c69154cbb1e57f3e`

## Server-side evidence

The APT-Cacher-NG access log recorded one upstream inbound transfer (`I`) and two outbound transfers (`O`) for the tested package.

The maintenance interface reported approximately:

- 3.0 MiB fetched upstream
- 5.8 MiB served
- 2.81 MiB of reported cache-hit data
- 48.81% data-cache efficiency across the displayed observation period

These aggregate statistics include other requests; they are not measurements exclusively attributable to the benchmark package.

## Persistence verification

The proxy was stopped through systemd, removing its Compose container, then recreated through the guarded startup unit.

The same package was requested after recreation:

- HTTP status: 200
- Elapsed time: 15.813 ms
- SHA-256: unchanged
- Persistent cache directory: approximately 3.1 MiB before and after
- Post-restart log showed an outbound package transfer without a new upstream fetch in the displayed log output
- Service state: active and enabled

## Enterprise applicability

The relevant architectural pattern is a shared dependency cache, not APT-Cacher-NG specifically.

Comparable enterprise approaches include:

| Lab implementation | Enterprise analogue |
|---|---|
| APT-Cacher-NG | Nexus/Artifactory repository proxy or an internal package mirror |
| Shared package reuse | Centralized dependency caching across CI workers |
| Persistent cache directory | Dedicated cache storage with retention and capacity management |
| Explicit proxy configuration | Build-environment dependency routing |
| Checksum validation | Artifact integrity and supply-chain verification |
| Monitoring via Uptime Kuma | Enterprise service monitoring and alerting |

For containerized builds, Docker BuildKit layer caching and cache mounts are complementary techniques. Prebuilt runner images can further reduce repeated package installation.

## Limitations

This is a single-package, two-request comparison—not a statistically meaningful CI benchmark.

The results do not establish a 13.1× improvement in complete pipeline execution time. HTTP repository requests were used for the cache test; opaque HTTPS tunnels should not be assumed to provide equivalent content caching.

APT package-signature verification must remain enabled.

Network source restrictions, operational capacity alerts, full-host reboot verification and long-term expiry behavior require separate validation.

**Status update:** The Gitea Actions runner is now operational. The cache is not yet a required CI dependency, so a full cold-versus-warm pipeline benchmark remains deferred until cache use is deliberately wired into a controlled build path.
