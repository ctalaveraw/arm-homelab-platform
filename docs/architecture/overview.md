# Platform Architecture

Updated 2026-11-17. Forgejo initial setup and sign-in as `ctalaveraw` are confirmed on LAN TCP/3002. Repository/data transfer, registry, runner and final LAN TCP/3000 acceptance remain pending. Caddy is prepared but not accepted. The [migration runbook](../runbooks/gitea-to-forgejo.md) tracks the transition; the [reference map](../runbooks/forgejo-reference-map.md) lists current names, paths and URLs.

## Source and recovery

GitHub is canonical, with protected `main` and PR-based changes. The local Forgejo repository will be a private pull mirror under `ctalaveraw/arm-homelab-platform`; it has not yet been populated. Recovery must remain possible without the R5C, its forge, Kubernetes or a future local secret service.

The fetch-only `forgejo` remote and `scripts/ops/check-source-parity.sh` compare GitHub, Forgejo and controller-local `main`. A successful check proves commit convergence, not backup completeness. Existing Gitea mirror acceptance remains recorded in the historical sprint reports.

## Independent management host

`gitops-controller-01` is the ARM64 NanoPi R5C. Its OS, Docker data root and SD-backed application state are distinct storage responsibilities. Ansible prepares service directories, installs storage guards and systemd units, and validates Compose configuration. Systemd owns guarded startup; application restart policy is `no`.

| Service | Purpose | Persistent state |
| --- | --- | --- |
| Forgejo | GitHub mirror and local OCI distribution | `services/forgejo` |
| Forgejo Runner | Repository-scoped trusted ARM64 validation | `services/forgejo-runner` |
| Caddy | HTTPS termination for the selected Git hostname | `services/caddy/data`, `services/caddy/config` |
| Gotify and Uptime Kuma | Notifications and availability checks | Separate service directories |
| APT-Cacher-NG | Optional package cache | Separate bounded cache directory |
| Prometheus and Grafana | Host and Kubernetes/Flux observability | Existing guarded observability storage |

All listed state paths are relative to `/srv/storage/state`. The actual ext4 filesystem must have label `storage_sdcard`; directory existence alone is insufficient. USB archive storage remains decommissioned.

## Ingress placement

Forgejo stays LAN/WireGuard-only. Its staging URL is `http://forgejo.lab.home.arpa:3002/`; the final LAN URL is `http://git.lab.home.arpa:3000/` after the legacy units are stopped and disabled. Git SSH remains LAN TCP/2223. Registered-domain HTTPS is optional follow-up work; public Zulip ingress is separate.

| System | Responsibility |
| --- | --- |
| OUTER router | WAN firewall, WireGuard, and only the reviewed inbound forwarding rules |
| INNER router | Transit/LAN routing, LAN DNS and the firewall path to the controller |
| R5C / Caddy | TLS certificates, HTTP-to-HTTPS redirects and hostname routing |
| Forgejo | Authentication, Git HTTP, API and OCI registry |

Caddy connects to Forgejo through the dedicated `platform_ingress` Docker network. Forgejo trusts only Caddy's configured IPv4 address for forwarded headers and leaves reverse-proxy authentication disabled. Its ordinary Docker network also serves the validation runner. The backend HTTP port is restricted to loopback after HTTPS acceptance. Git SSH uses a separate LAN-bound port and is not handled by Caddy's HTTP proxy.

The ingress subnet and container addresses in `.env.example` are candidates. Check them against host, LAN, VPN and Docker routes before deployment. A dedicated ingress host can replace this placement later without moving the routers' responsibilities.

## Delivery and compute

The compute plane is the existing upstream kubeadm cluster with one Raspberry Pi control plane and two workers. A fourth Pi is reserved for reconstruction tests.

GitHub-hosted ARM64 CI validates the repository, builds `platform-hello` once, tests the same image, and applies Trivy vulnerability and secret checks. A separate publisher receives an image archive plus checksum and expected Docker image ID, verifies that handoff, and publishes to GHCR with `packages: write`.

Registry replication uses Skopeo with digest preservation. Independent retrieval tests fetch the complete OCI artifact into a fresh layout. Forgejo package association is separate registry metadata. Kubernetes currently pulls the qualified GHCR digest; changing the local forge does not require changing workload image references.

Flux pulls canonical Git desired state and reconciles only the selected application namespace using scoped authority. The validation runner has no production Docker socket, deployment credentials or Kubernetes authority. A future operations runner must have its own identity and approval boundary; it must not compete with Flux for routine application reconciliation.

## Observability and outstanding acceptance

Prometheus and Grafana run outside Kubernetes with bounded retention/storage. Native exporters cover the R5C and three physical Pi hosts. A separate read-only TLS observer scrapes the Kubernetes API and Flux metrics through constrained RBAC. Historical evidence records eight healthy targets and five provisioned dashboards.

Revalidate mirror synchronization, runner execution, OCI parity, monitor targets and source parity on Forgejo. Both LAN forge names resolve to `10.0.0.50`; private HTTPS remains pending. No public Forgejo forwarding is needed. Backup restoration, blank-host reconstruction, service-level alerting and Kubernetes object-state coverage remain separate work.

Historical records: [native CI](../sprints/07-native-gitea-ci.md), [OCI distribution](../sprints/09-dual-oci-distribution.md), [Flux](../sprints/12-flux-gitops.md), [telemetry](../sprints/14-kubernetes-flux-telemetry.md).
