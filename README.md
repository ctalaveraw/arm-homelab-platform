# ARM Homelab Platform

[![ARM Platform CI](https://github.com/ctalaveraw/arm-homelab-platform/actions/workflows/platform-ci.yml/badge.svg)](https://github.com/ctalaveraw/arm-homelab-platform/actions/workflows/platform-ci.yml)

A platform engineering lab for reproducible infrastructure, ARM64 application delivery, observability and recovery.

**Deployment status — 2026-11-18:** Forgejo is healthy on the independent NanoPi R5C (`gitops-controller-01`) at `http://git.lab.home.arpa:3000/`, with owner `ctalaveraw` and SSH on `2223`. The GitHub mirror and linked `platform-hello` package were transferred and verified during staging; the repository-scoped runner is active. Legacy Gitea units are stopped and disabled, with separate state retained for rollback. Post-cutover source parity, full OCI retrieval, native Actions and Kuma availability now pass. Remaining retirement and permission/metadata review are tracked in the migration checklist. See the [migration record](docs/runbooks/gitea-to-forgejo.md) and [name/path reference](docs/runbooks/forgejo-reference-map.md).

| Component | Repository configuration | Last recorded runtime evidence |
| --- | --- | --- |
| Local forge | Forgejo 15.0.11 LTS; new SD-backed state | LAN HTTP/3000 health passed; mirror parity, SSH read and complete OCI retrieval passed during staging |
| Local validation | Forgejo Runner 13.1.0; repository scope; UID 10001 | Manual and push-triggered native runs succeeded; service active after cutover |
| Public app ingress | cloudflared 2026.11.1 → internal Caddy 2.11.9; no host ports | Configuration prepared; tunnel/app acceptance pending |
| Chat application | Controller Zulip 13.2-0; private database/queue/caches | Placement selected; initialization and live acceptance pending |
| Application delivery | GitHub ARM64 CI, GHCR and Flux | Build/test/scan, digest preservation, deployment and rollback verified |
| Observability | Prometheus, Grafana, native exporters and read-only Kubernetes observer | Eight Prometheus targets and five dashboards |

## Architecture

GitHub remains the canonical source and external recovery copy. Forgejo provides a private one-way pull mirror, local validation and an OCI distribution endpoint. Promoted artifacts retain their tested registry digest; Kubernetes runs the GHCR digest and Flux reconciles application desired state from GitHub.

The R5C remains outside the Kubernetes cluster. Ansible manages the host baseline and guarded systemd/Compose services. Persistent service state lives under `/srv/storage/state/services`; startup guards require the actual `storage_sdcard` ext4 filesystem and reject redirected or incorrect bind sources. Docker's own data root remains on eMMC.

The selected profile runs Zulip, its database/queue/caches, cloudflared and internal Caddy in separate controller containers. Cloudflare Tunnel makes outbound connections; this profile needs no inbound web forwarding. Forgejo remains private and has no public Caddy/tunnel route. OUTER/INNER retain routing, firewall, DNS, WireGuard and unrelated DDNS roles. See [Cloudflare Tunnel deployment](docs/runbooks/cloudflared.md) and [domain ingress](docs/runbooks/domain-ingress.md).

## Forgejo migration

Gitea 1.27.3 cannot use Forgejo's supported in-place database upgrade. Forgejo was initialized in a new `/srv/storage/state/services/forgejo` directory beside Gitea on HTTP/3002. The verified mirror and OCI artifact remain in that same new state while Forgejo serves LAN HTTP/3000 and SSH/2223. The old Gitea units are disabled. Existing Gitea state, credentials and runner identity must not be copied into Forgejo.

Follow the [migration runbook](docs/runbooks/gitea-to-forgejo.md) to:

1. Capture a consistent backup and inventory local-only data.
2. Start Forgejo beside the legacy instance.
3. Recreate the GitHub mirror, transfer required metadata, and replicate OCI artifacts without rebuilding.
4. Register a new restricted runner and verify native validation.
5. Stop and disable legacy Gitea, move Forgejo to `http://git.lab.home.arpa:3000/`, and update clients and monitoring using owner `ctalaveraw`.
6. Retire the old services after acceptance; retain their backup and rollback manifests.

Private HTTPS can follow separately; it is not a prerequisite for this LAN port cutover.

Historical sprint reports, incidents and screenshots retain their original Gitea names. They establish the prior baseline and do not prove Forgejo acceptance.

## Configuration and lifecycle

Copy the relevant `.env.example` files to local `.env` files. Local credentials, runner configuration and private keys are excluded from Git. Ansible playbooks run from the controller checkout at `/srv/platform`.

The Forgejo example retains the parallel-migration settings. The live controller's local `.env` instead uses `FORGEJO_FQDN=git.lab.home.arpa`, `FORGEJO_ROOT_URL=http://git.lab.home.arpa:3000/` and `FORGEJO_HTTP_PORT=3000`; SSH remains `2223`.

| Playbook | Responsibility |
| --- | --- |
| `00-preflight.yml` | ARM64, SD mount and filesystem baseline |
| `01-management.yml` | Host tools, Docker, Kubernetes and Flux clients |
| `02-forgejo.yml` | Forgejo storage guard and service |
| `03-forgejo-runner.yml` | Registered validation runner lifecycle |
| `04-gotify.yml` | Notifications |
| `05-uptime-kuma.yml` | Availability monitoring |
| `06-apt-cacher-ng.yml` | Optional package cache |
| `07-prometheus.yml`, `08-grafana.yml` | Bounded management observability |
| `09-node-exporter.yml`, `10-pi-exporters.yml` | Host and Pi exporters |
| `11-caddy.yml` | Separate private Forgejo HTTPS candidate; not a public tunnel target |
| `caddy-public.yml` | Prepare controller Zulip/tunnel/Caddy; explicit activation after local secrets setup |

Systemd owns startup; Compose restart policies cannot bypass storage guards. Apply configuration changes with explicit restarts after reviewing them. Running a playbook with `state: started` does not recreate an already running container automatically.

## Validation

```bash
bash scripts/ci/bootstrap.sh
bash scripts/ci/validate.sh
```

GitHub-hosted ARM64 CI also validates the Caddyfile with the pinned Caddy image and builds/smoke-tests the Forgejo runner image. Those checks do not prove home DNS, WAN routing, certificate issuance, data migration or application recovery.

## Documentation

- [Documentation index](docs/README.md)
- [Architecture and trust boundaries](docs/architecture/overview.md)
- [CI, mirroring and OCI distribution](docs/ci.md)
- [Forgejo migration and rollback](docs/runbooks/gitea-to-forgejo.md)
- [Forgejo names, paths and consumer URLs](docs/runbooks/forgejo-reference-map.md)
- [Domain and HTTPS ingress](docs/runbooks/domain-ingress.md)
- [Cloudflare Tunnel in Docker](docs/runbooks/cloudflared.md)
- [Controller public application ingress](docs/runbooks/controller-public-ingress.md)
- [Zulip on the controller](docs/runbooks/zulip-controller.md)
- [Forgejo and controller ingress decision](docs/adr/0015-forgejo-and-controller-ingress.md)
- [Engineering evidence ledger](docs/interview/engineering-evidence.md)
- [Platform charter](docs/vision/platform-charter.md)
- [Objective register](docs/planning/objectives.md), [roadmap](docs/roadmap.md) and [backlog](docs/backlog.md)

Off-device restore, blank-host reconstruction, wider service telemetry, runtime alerting and remaining management HTTPS routes still require acceptance. The recovery targets of four hours RTO and one hour RPO remain goals.
