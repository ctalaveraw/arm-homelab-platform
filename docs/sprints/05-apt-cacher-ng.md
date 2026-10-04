# OPS-006 — Shared APT Cache

Date: 2026-10-04
Status: Operational; network access-control verification pending.

## Implementation

- Deployed APT-Cacher-NG using an ARM64-compatible container image.
- Established persistent cache storage under `/srv/storage/state/services/apt-cacher-ng`.
- Reused the Ansible-managed storage preflight, Python Compose guard and systemd lifecycle.
- Added declarative Compose validation, service activation and boot enablement to `05-apt-cacher-ng.yml`.
- Added `apt-cache.lab.home.arpa` through OpenWRT DNS.
- Added an Uptime Kuma HTTP monitor for the maintenance interface.

## Verification

- Initial directory creation: `changed=1`.
- Subsequent execution: `changed=0`.
- Systemd installation created two managed artifacts.
- Installed Python executable matched its source.
- Positive storage guard passed; incorrect storage override rejected.
- Image architecture confirmed as `linux/arm64`.
- HTTP readiness returned 200.
- Real Debian repository request succeeded through the explicit proxy.
- Updated activation playbook enabled the service.
- Subsequent activation execution converged with `changed=0`.

## Performance

An identical versioned ARM64 `coreutils` package was downloaded twice.

- First request: 199.713 ms
- Second request: 15.229 ms
- Approximately 13.1× faster for this individual retrieval
- Both SHA-256 checksums matched
- Server-side log showed upstream retrieval followed by cache reuse

The detailed benchmark is recorded in `docs/benchmarks/2026-10-04-apt-cacher-ng.md`.

## Recovery validation

The Compose container was removed through systemd stop and recreated through guarded startup.

- Pre-restart package and post-restart package were byte-identical.
- Post-restart request completed in 15.813 ms.
- Cache directory remained approximately 3.1 MiB.
- Service verified active and enabled.

## Maintenance and limitations

- Existing daily maintenance script discovered.
- Configuration included `ExThreshold: 4`.
- Long-term expiry execution has not been independently tested.
- Proposed initial capacity-alert threshold: 5 GiB (not a hard quota).
- Network source restrictions require verification before broad client use.
- The host-wide APT configuration was intentionally left independent of the cache.
- Full machine reboot and off-device recovery remain untested.

## Next experiment

Measure actual cold versus warmed dependency-installation stages after the Gitea Actions runner becomes operational.
