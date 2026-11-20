# Deployment standards and service map

Reviewed against repository source and operator reports on 2026-11-18. This is
the current deployment contract. The [objective register](../planning/objectives.md)
tracks controls that still need implementation or physical verification.

## Names and ownership

| Term | Meaning in this repository |
| --- | --- |
| Host | An Ansible inventory target; the R5C is the independent management controller |
| Compose project | A named group of containers and networks, such as `caddy-public` |
| Compose service | A component inside a project, such as `server`, `zulip` or `database` |
| systemd unit | The startup, shutdown and storage-check boundary; it can own a whole project or one selected service |
| Playbook | Host preparation and declared activation; numbered files describe the established deployment sequence |
| Overlay | A manifest that requires a specified base; it is not a second independently deployable service |

Keep existing project names, unit names, paths and Docker DNS aliases stable.
For example, `server` in the public ingress project is Caddy, while `server` in
the Forgejo project is Forgejo. Those aliases have separate network scopes.
The tunnel's `http://server:8080` target depends on the public alias.

The named `caddy-public.yml` playbook prepares an independently activated stack;
it does not replace `11-caddy.yml`, which prepares optional private Forgejo HTTPS.
Renumbering a playbook or renaming a live project needs an explicit migration.

## Repository layout

| Path | Source responsibility |
| --- | --- |
| `ansible/` | Host inventories, roles and service preparation/activation playbooks |
| `compose/` | Controller runtime manifests, configuration templates, units and storage guards |
| `apps/` | Application source and application Dockerfiles, currently `platform-hello` |
| `images/` | Supporting execution-image builds, currently the Forgejo validation runner |
| `deploy/kubernetes/` | Application manifests and separately administered access/observer bootstrap resources |
| `clusters/home-pi/` | Flux installation hardening, source and reconciliation declarations |
| `scripts/ci/` | Portable validation and build/test/scan/artifact-publication helpers |
| `scripts/ops/` | Explicit operator tools for deployment, source parity and OCI distribution |
| `scripts/zulip/`, `scripts/cloudflared/` | Service-specific installers, combined Compose wrapper and public-proxy smoke check |
| `.github/workflows/`, `.forgejo/workflows/` | Hosted pipeline authority and restricted local validation respectively |
| `docs/` | Current contracts/procedures, planning and dated evidence as classified below |

Zulip uses upstream images and an attributed Compose adaptation; it does not add
application source under `apps/`. Credentials, persistent state and recovery
archives belong outside this source tree.

## Source and lifecycle map

Paths in the manifest column are relative to `compose/`; playbooks are under
`ansible/playbooks/`. Every listed stateful unit declares an SD guard.

| Deployment | Manifest | Playbook | systemd owner | State below `/srv/storage/state/services/` |
| --- | --- | --- | --- | --- |
| Forgejo | `forgejo/compose.yml` | `02-forgejo.yml` | `forgejo.service` | `forgejo/` |
| Validation runner | `forgejo-runner/compose.yml` | `03-forgejo-runner.yml` | `forgejo-runner.service` | `forgejo-runner/` |
| Notifications | `gotify/compose.yml` | `04-gotify.yml` | `gotify.service` | `gotify/` |
| Availability | `uptime-kuma/compose.yml` | `05-uptime-kuma.yml` | `uptime-kuma.service` | `uptime-kuma/` |
| Optional APT cache | `apt-cacher-ng/compose.yml` | `06-apt-cacher-ng.yml` | `apt-cacher-ng.service` | `apt-cacher-ng/` |
| Prometheus | `observability/compose.yml`, service `prometheus` | `07-prometheus.yml` | `prometheus.service` | `prometheus/`, `prometheus-auth/` |
| Grafana | `observability/compose.yml`, service `grafana` | `08-grafana.yml` | `grafana.service` | `grafana/`, `grafana-auth/` |
| Optional private Forgejo HTTPS | `caddy/compose.yml` | `11-caddy.yml` | `caddy.service` | `caddy/` |
| Public Zulip and ingress | `caddy-public/compose.yaml` + `zulip/compose.yaml` | `caddy-public.yml` | `caddy-public.service` | `caddy-public/`, `cloudflared/`, `zulip/` |

Native Node Exporters use `09-node-exporter.yml` and `10-pi-exporters.yml` with
`node-exporter.service`; they are not Compose projects. Kubernetes application
resources belong in `deploy/kubernetes/`, and Flux source/reconciliation objects
belong in `clusters/home-pi/`. Ansible owns host preparation; Flux owns routine
application reconciliation. The validation runner owns neither.

Both `.yml` and `.yaml` are supported. General CI renders every tracked
`compose/*/compose.yml` and `compose/*/compose.yaml`. Zulip renders with its base.
The retained `caddy-public/zulip-upstream.override.yaml` is an inactive
compatibility example for the earlier separate-host bundle, not a supported
controller entry point. Generic YAML parsing covers that example; controller
activation always uses the two files in the table.

## Startup and shutdown

The [guarded lifecycle decision](../adr/0004-guarded-compose-lifecycle.md) requires
the mounted ext4 filesystem labeled `storage_sdcard`, canonical bind sources,
`create_host_path: false`, and Compose `restart: "no"`. Docker's data root remains
on eMMC. A mount directory alone does not satisfy the storage contract.

Use the installed unit for routine start, stop and restart. An active oneshot
normally reports `ActiveState=active`, `SubState=exited`; inspect containers and
application probes separately. These units do not continuously supervise container
health. Ansible restart handlers vary by service, and `state: started` alone does
not apply a changed Compose environment to an already running project.

Public ingress owns all seven chat containers. Its restart also restarts Zulip,
the database, RabbitMQ, Redis and Memcached. It waits up to 900 seconds for Compose
readiness inside a 1200-second unit startup timeout. Failed startup runs cleanup
without removing bind-mounted state. `zulip-compose` is the manual interface for
that same combined project; there is no separate `zulip.service`.

Prometheus and Grafana share a project but have separate guards and units. Their
units stop the selected service rather than running project-wide `down`. Use those
units to avoid stopping the other monitoring component.

## Configuration, credentials and permissions

Use each deployment's `.env.example` as its configuration schema. Public ingress
and Zulip share `compose/caddy-public/.env`; observability currently uses committed
configuration and protected file secrets with `--env-file /dev/null`. Credentials
and deployment-specific public chat values stay outside Git.

Ownership and traversal follow the runtime identity and mount, not a blanket mode
for every directory. The public Caddyfile is 0644, Zulip's application data mount
is root-owned 0755, its private host parent is 0700, and its six source credential
files are root-owned 0444 inside a 0700 directory. The tunnel token instead uses
root ownership, group 65532 and mode 0440. Preparation preserves image-managed
database, queue and Redis ownership. See the [operator runbook](../runbooks/zulip-controller.md).

Preserve existing credentials when preparing or upgrading a deployment. Hidden-input
installers keep tokens and passwords out of shell history and process arguments.
Protect off-device copies of original configuration and credentials independently
of Forgejo and any future secret service.

## Exposure and image policy

Published host ports require an explicit bind address. Forgejo and management
services use their documented private bindings; Prometheus is loopback-bound.
Public chat publishes no host ports. Its tunnel, application proxy and dependency
networks remain separate from Forgejo. Docker's `PORTS` display can list an image's
exposed ports without a host mapping; verify mappings rather than that list alone.

Runtime hardening is service-specific. The connector uses UID/GID 65532, and the
validation runner uses 10001. Caddy and several monitoring components drop all
capabilities. The official Zulip image needs its root entrypoint for setup and
runs application management commands as `zulip`; setting a blanket container user
or read-only filesystem would require upstream compatibility testing.

Kubernetes `platform-hello` uses a digest. cloudflared is pinned by tag and digest.
Other vendor services use version, series or distribution tags; examples include
`rabbitmq:4.2`, `memcached:alpine`, `redis:alpine` and `mbentley/apt-cacher-ng:trixie`.
The runner uses a local `:dev` build. Those references are not immutable pins.
Image update policy and reproducible runner identity remain CI-008 and SEC-014 work.

The seven chat container memory limits total 3 GiB. They are ceilings, not reserved
memory or proof that the 4 GB host can sustain every management service together.
Review actual usage, swap and SD latency before resuming the monitoring stack or
increasing chat load.

## Evidence and documentation

| Location | Purpose |
| --- | --- |
| `docs/architecture/` | Current topology, deployment map and operating contracts |
| `docs/runbooks/` | Current procedures, diagnostics and accepted/pending operator checks |
| `docs/adr/` | Decisions and consequences; update implementation status when evidence changes |
| `docs/planning/`, roadmap and backlog | Stable work IDs, dependencies, status and acceptance tiers |
| `docs/sprints/`, `docs/incidents/`, `docs/benchmarks/` | Dated records; retain historical service names |
| `docs/interview/` | Dated engineering evidence with limits and source references |

Portable checks (P), simulated checks (S) and physical/site checks (H) are distinct.
Hosted CI does not prove home DNS, mail delivery, reboot recovery or restoration.
The latest operator inventory showed healthy public chat but stopped Prometheus
and Grafana containers; earlier eight-target/five-dashboard acceptance remains
historical. No current memory, SD latency or alert coverage is inferred from it.

Remaining standardization work includes environment-driven observability bindings
(OPS-013), budgets/hardening for older services (OPS-018, SEC-016), immutable update
policy (SEC-014), monitoring restart/alert checks (PLAT-012/013), and isolated
recovery (PLAT-017/018 and DR work). These are documented gaps, not changes to live
services made by this review.
