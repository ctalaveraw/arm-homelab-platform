# ARM Homelab Platform

[![ARM Platform CI](https://github.com/ctalaveraw/arm-homelab-platform/actions/workflows/platform-ci.yml/badge.svg)](https://github.com/ctalaveraw/arm-homelab-platform/actions/workflows/platform-ci.yml)

A platform engineering lab for reproducible infrastructure, ARM64 application delivery, observability and recovery.

**Deployment transition — 2026-11-17:** This repository targets Forgejo 15.0.11 LTS, Forgejo Runner and Caddy on the independent NanoPi R5C (`gitops-controller-01`). The last verified host baseline used Gitea 1.27.3. Migration, Forgejo runner acceptance, certificates and domain routing require host-side deployment and verification. The [migration runbook](docs/runbooks/gitea-to-forgejo.md) defines the cutover and rollback.

| Component | Repository configuration | Last recorded runtime evidence |
| --- | --- | --- |
| Local forge | Forgejo 15.0.11 LTS; new SD-backed state | Gitea 1.27.3; private GitHub pull mirror and OCI registry |
| Local validation | Forgejo Runner 13.1.0; repository scope; UID 10001 | Gitea runner; ARM64 validation and mirror push trigger |
| HTTPS ingress | Caddy 2.11.9 on the R5C | Management services used LAN HTTP |
| Application delivery | GitHub ARM64 CI, GHCR and Flux | Build/test/scan, digest preservation, deployment and rollback verified |
| Observability | Prometheus, Grafana, native exporters and read-only Kubernetes observer | Eight Prometheus targets and five dashboards |

## Architecture

GitHub remains the canonical source and external recovery copy. Forgejo provides a private one-way pull mirror, local validation and an OCI distribution endpoint. Promoted artifacts retain their tested registry digest; Kubernetes runs the GHCR digest and Flux reconciles application desired state from GitHub.

The R5C remains outside the Kubernetes cluster. Ansible manages the host baseline and guarded systemd/Compose services. Persistent service state lives under `/srv/storage/state/services`; startup guards require the actual `storage_sdcard` ext4 filesystem and reject redirected or incorrect bind sources. Docker's own data root remains on eMMC.

Caddy terminates HTTPS on the controller and forwards only the configured Git hostname to Forgejo. OUTER owns WAN access and forwarding; INNER owns LAN routing, firewall policy and DNS. See [domain ingress](docs/runbooks/domain-ingress.md) for public and private access requirements.

## Forgejo migration

Gitea 1.27.3 cannot use Forgejo's supported in-place database upgrade. Forgejo uses a new `/srv/storage/state/services/forgejo` directory and temporary HTTP/SSH ports `3002`/`2223`. Existing Gitea state, credentials and runner identity must not be copied into it.

Follow the [migration runbook](docs/runbooks/gitea-to-forgejo.md) to:

1. Capture a consistent backup and inventory local-only data.
2. Start Forgejo beside the legacy instance.
3. Recreate the GitHub mirror, transfer required metadata, and replicate OCI artifacts without rebuilding.
4. Register a new restricted runner and verify native validation.
5. Add the registered hostname and HTTPS, then update clients and monitoring.
6. Retire the old services after acceptance; retain their backup and rollback manifests.

Historical sprint reports, incidents and screenshots retain their original Gitea names. They establish the prior baseline and do not prove Forgejo acceptance.

## Configuration and lifecycle

Copy the relevant `.env.example` files to local `.env` files. Local credentials, runner configuration and private keys are excluded from Git. Ansible playbooks run from the controller checkout at `/srv/platform`.

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
| `11-caddy.yml` | HTTPS ingress and persistent certificate state |

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
- [Domain and HTTPS ingress](docs/runbooks/domain-ingress.md)
- [Forgejo and controller ingress decision](docs/adr/0015-forgejo-and-controller-ingress.md)
- [Engineering evidence ledger](docs/interview/engineering-evidence.md)
- [Platform charter](docs/vision/platform-charter.md)
- [Objective register](docs/planning/objectives.md), [roadmap](docs/roadmap.md) and [backlog](docs/backlog.md)

Off-device restore, blank-host reconstruction, wider service telemetry, runtime alerting and remaining management HTTPS routes still require acceptance. The recovery targets of four hours RTO and one hour RPO remain goals.
