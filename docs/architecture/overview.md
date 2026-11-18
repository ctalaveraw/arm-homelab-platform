# Platform architecture

Current deployment, reviewed 2026-11-18.

## Source and recovery

GitHub owns canonical source and protected `main`. Forgejo holds the one-way pull mirror at `ctalaveraw/arm-homelab-platform`, runs repository-scoped validation and serves a linked OCI package. Routine writes go to GitHub.

The fetch-only `forgejo` remote and `scripts/ops/check-source-parity.sh` compare local, GitHub and Forgejo `main`. Parity, SSH access and full OCI retrieval passed after the migration. The [migration record](../runbooks/gitea-to-forgejo.md) contains the accepted revisions and digest.

Recovery source and credentials must be accessible without the R5C, Forgejo, Kubernetes or a future OpenBao service. Consistent checkpoints and an off-device checksum have been verified; a full restore and fresh-host rebuild remain untested.

## Independent management host

`gitops-controller-01` is a NanoPi R5C at `10.0.0.50`. It runs outside the three-node kubeadm cluster. Ansible manages packages, directories, guards and systemd units. Systemd starts Compose services only after their storage checks pass.

| Service | Role | State under `/srv/storage/state` |
| --- | --- | --- |
| Forgejo | GitHub pull mirror and OCI registry | `services/forgejo` |
| Forgejo Runner | Trusted main-branch ARM64 validation | `services/forgejo-runner` |
| Gotify / Uptime Kuma | Notifications and availability | Separate service directories |
| APT-Cacher-NG | Optional package cache | Separate cache directory |
| Prometheus / Grafana | Host, Kubernetes API and Flux metrics | Guarded observability directories |
| Private Caddy profile | Optional Forgejo HTTPS; not deployed for the current LAN URL | `services/caddy/data`, `services/caddy/config` |

Application data uses the actual ext4 filesystem labeled `storage_sdcard`. Guards reject missing mounts, redirected paths and incorrect bind sources. Docker's data root stays on eMMC. The former USB archive is decommissioned.

## Ingress placement

| Access | Endpoint or path | Status |
| --- | --- | --- |
| Forgejo HTTP / OCI | `http://git.lab.home.arpa:3000/` | LAN/WireGuard; health and OCI retrieval passed |
| Forgejo SSH | TCP `2223` | LAN-bound; repository read passed |
| Forgejo HTTPS | Separate `compose/caddy` profile | Optional; private certificate deployment remains open |
| Public Zulip | Cloudflare edge → cloudflared → internal Caddy → Zulip | Separate controller profile; live application acceptance tracked in its runbook |

Both `git.lab.home.arpa` and `forgejo.lab.home.arpa` resolve to the controller. Forgejo HTTP is bound to the controller's LAN address. There is no public Forgejo tunnel route.

OUTER handles the WAN firewall and WireGuard. INNER handles LAN routing and DNS. The public chat profile makes outbound Cloudflare connections and needs no inbound web forwarding. See [domain ingress](../runbooks/domain-ingress.md) and [controller public ingress](../runbooks/controller-public-ingress.md).

Forgejo's configuration includes a separate `platform_ingress` network for the optional private Caddy profile. Forwarded-header trust is limited to the configured proxy address; proxy authentication is disabled. If private HTTPS is deployed, verify certificates and access first, then restrict the HTTP binding to loopback. Git SSH remains a separate service.

## Delivery and compute

The kubeadm cluster has one Raspberry Pi control plane and two workers; a fourth Pi is reserved for reconstruction exercises.

GitHub ARM64 CI builds `platform-hello`, tests that image and scans it with Trivy. The publisher verifies an image archive, checksum and Docker image ID before publishing to GHCR. Skopeo copies existing OCI content with digest preservation. Full retrieval and package association are checked separately.

Flux reads desired state from GitHub and reconciles the application namespace through its scoped ServiceAccount. Kubernetes uses the qualified GHCR digest. A local forge migration does not change those sources.

The Forgejo validation runner has no production Docker socket, deployment credential or Kubernetes authority. A future operations runner needs a separate identity and execution boundary. Flux continues to own routine application reconciliation.

## Monitoring and remaining work

The accepted telemetry deployment has eight Prometheus targets and five Grafana dashboards. Host exporters cover the R5C and three Pis. A read-only X.509 observer scrapes the Kubernetes API and Flux metrics through the API endpoint.

Forgejo native validation passed for manual and mirrored-push runs. Kuma reports availability, and the operator updated its target to `http://git.lab.home.arpa:3000/api/healthz`. Alert delivery after migration has not been retested.

Remaining work includes private HTTPS, exporter network isolation, an induced scrape outage, wider workload/service metrics, scheduled encrypted backups, restore and blank-host reconstruction. Details are in the [backlog](../backlog.md).

Historical records: [native Gitea CI](../sprints/07-native-gitea-ci.md), [OCI distribution](../sprints/09-dual-oci-distribution.md), [Flux](../sprints/12-flux-gitops.md) and [telemetry](../sprints/14-kubernetes-flux-telemetry.md).
