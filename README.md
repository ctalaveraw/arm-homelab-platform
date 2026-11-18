# ARM Homelab Platform

[![ARM Platform CI](https://github.com/ctalaveraw/arm-homelab-platform/actions/workflows/platform-ci.yml/badge.svg)](https://github.com/ctalaveraw/arm-homelab-platform/actions/workflows/platform-ci.yml)

An ARM64 lab for managing hosts with Ansible, delivering container images through CI and Flux, and testing monitoring and recovery.

## Current deployment

The NanoPi R5C (`gitops-controller-01`, `10.0.0.50`) runs outside the Kubernetes cluster. Forgejo replaced Gitea on 2026-11-18.

| Component | Configuration | Verified behavior |
| --- | --- | --- |
| Local Git and OCI registry | Forgejo 15.0.11 LTS at `http://git.lab.home.arpa:3000/`; SSH `2223` | GitHub/local/mirror parity, SSH access, preserved OCI digest and full artifact retrieval |
| Local validation | Forgejo Runner 13.1.0; repository scope; UID/GID 10001 | Manual and mirrored-push Actions runs succeeded |
| Availability | Uptime Kuma | Forgejo monitor updated to `/api/healthz`; HTTP health passed |
| Application delivery | GitHub ARM64 CI, GHCR and Flux | Build/test/scan, verified image transfer, digest deployment and rollback |
| Metrics | Prometheus, Grafana, host exporters and Kubernetes/Flux observer | Eight scrape targets and five dashboards in the last acceptance record |
| Public chat profile | Zulip 13.2-0, cloudflared 2026.11.1 and internal Caddy 2.11.9 | Configuration and CI checks are present; end-to-end public chat acceptance is tracked separately |

GitHub is the canonical source. Forgejo holds the one-way pull mirror at `ctalaveraw/arm-homelab-platform` and a linked `platform-hello` container package. Routine changes go through GitHub PRs. Flux reads GitHub and deploys the GHCR image by digest.

Forgejo is limited to LAN/WireGuard access. It has no public Caddy or Cloudflare Tunnel route. The public chat profile uses an outbound tunnel and publishes no host web ports. OUTER and INNER retain routing, firewall, DNS, WireGuard and unrelated DDNS duties.

## Host and storage

Ansible configures the R5C and installs systemd units. Each stateful Compose service checks the mounted `storage_sdcard` ext4 filesystem and its bind sources before starting. Persistent service data lives under `/srv/storage/state/services`; Docker's data root stays on eMMC.

Systemd owns service startup. Compose restart policies are disabled so Docker cannot bypass the storage checks. Configuration or image changes require an explicit service restart; Ansible `state: started` alone does not recreate running containers.

## Forgejo migration

Forgejo uses separate state at `/srv/storage/state/services/forgejo`. The former Gitea 1.27.3 database was not converted. The GitHub mirror and published package were transferred, a new runner was registered, and Forgejo took over HTTP/3000 while retaining SSH/2223.

The old Gitea services are stopped and disabled. Their state, images, manifests and verified private backups remain available for rollback. See the [migration record and rollback procedure](docs/runbooks/gitea-to-forgejo.md) and [current names, paths and client URLs](docs/runbooks/forgejo-reference-map.md). Dated sprint and incident reports describe the software used at the time.

## Configuration and lifecycle

Run playbooks from the controller checkout at `/srv/platform`. Use the service's `.env.example` to prepare its local `.env`; retain existing credentials when updating an installation. Local secrets, runner registration and private keys stay outside Git.

The Forgejo example matches the current LAN URL and port. Bind addresses must be supplied explicitly. A new parallel migration must override HTTP to `3002` before starting beside Gitea, as described in the migration runbook.

| Playbook | Responsibility |
| --- | --- |
| `00-preflight.yml` | ARM64, SD mount and filesystem checks |
| `01-management.yml` | Host packages, Docker, Kubernetes and Flux clients |
| `02-forgejo.yml` | Forgejo storage guard and service |
| `03-forgejo-runner.yml` | Registered validation runner lifecycle |
| `04-gotify.yml` | Notifications |
| `05-uptime-kuma.yml` | Availability monitoring |
| `06-apt-cacher-ng.yml` | Optional package cache |
| `07-prometheus.yml`, `08-grafana.yml` | Prometheus and Grafana |
| `09-node-exporter.yml`, `10-pi-exporters.yml` | Host and Pi exporters |
| `11-caddy.yml` | Optional private Forgejo HTTPS profile |
| `caddy-public.yml` | Prepare the controller Zulip/tunnel/Caddy stack; activate after local configuration |

## Validation

```bash
bash scripts/ci/bootstrap.sh
bash scripts/ci/validate.sh
```

GitHub-hosted ARM64 CI also validates Caddy, builds the Forgejo runner, and builds, tests and scans the application. The controller ingress workflow tests its proxy and Zulip profile with disposable settings. Home DNS, tunnel connectivity, SMTP and recovery require live checks.

## Documentation

Start with the [documentation index](docs/README.md), [architecture](docs/architecture/overview.md) and [CI guide](docs/ci.md). Operations guides cover [Forgejo migration](docs/runbooks/gitea-to-forgejo.md), [domain ingress](docs/runbooks/domain-ingress.md), [Cloudflare Tunnel](docs/runbooks/cloudflared.md) and [controller Zulip](docs/runbooks/zulip-controller.md).

The [roadmap](docs/roadmap.md), [backlog](docs/backlog.md) and [objective register](docs/planning/objectives.md) track unfinished work. Off-device restore, blank-host reconstruction, runtime alerts and private management HTTPS remain open. The four-hour RTO and one-hour RPO are recovery targets.
