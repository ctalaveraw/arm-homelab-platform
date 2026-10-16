# Kubernetes API and Flux Telemetry — Operations

Scope: PLAT-012 Kubernetes API server and Flux controller scrape jobs from the out-of-cluster NanoPi R5C. Physical Pi Node Exporter troubleshooting remains in the [host telemetry runbook](observability-host-metrics.md); runtime Gotify alerting is a **separate PLAT-013** concern.

## Data path and security

R5C Prometheus -> `https://10.0.0.5:6443` -> (a) authenticated API server `/metrics`, (b) API-server Service proxy to metrics-only Flux source-controller and kustomize-controller Services in `flux-system`. R5C cannot directly reach the Pod CIDR or Kubernetes Service VIP in the measured setup. All three API-mediated jobs may fail together if the API server is unavailable.

The observer certificate has `CN=platform-observer`, not a privileged `O=system:masters` identity. Separate RBAC limits it to specific metrics paths; denies Secrets, Node inventories, deployment listing, Pod proxy and mutation operations. The monitoring RBAC and Service bootstrap is **not** managed by ordinary application Flux GitOps. See [ADR-0014](../adr/0014-kubernetes-telemetry-observer.md).

The original observer credentials stay under `~runner/.kube/platform-observer/` on the R5C (private files never committed). Ansible installs protected runtime copies under `/srv/storage/state/services/prometheus-auth`, with supplemental group `29012` and a read-only Prometheus bind at `/run/secrets/platform-observer`. Do not print private keys, embed them in shell arguments, or copy kubeadm/deployer credentials into the exporter.

## Observe without changing production

From an interactive R5C session, after verifying you are on the correct host and the declared SD filesystem is mounted:

```bash
systemctl is-active prometheus.service grafana.service
curl -fsS http://127.0.0.1:9090/-/ready
curl -fsS http://10.0.0.50:3300/api/health
curl -fsSG --data-urlencode 'query=up{job="kubernetes-apiserver"}' http://127.0.0.1:9090/api/v1/query
curl -fsSG --data-urlencode 'query=up{job="flux-source-controller"}' http://127.0.0.1:9090/api/v1/query
curl -fsSG --data-urlencode 'query=up{job="flux-kustomize-controller"}' http://127.0.0.1:9090/api/v1/query
curl -fsS 'http://127.0.0.1:9090/api/v1/targets?state=active'
openssl x509 -in "$HOME/.kube/platform-observer/client.crt" -noout -subject -enddate
```

Check three Kubernetes/Flux jobs `up=1` **and** fresh `lastScrape` values, positive `scrape_samples_post_metric_relabeling`, expected stable labels, and relevant panel time ranges. Both endpoints should be running with their declared non-root UID/GID and resource limits. Grafana dashboards are *Kubernetes API — Control Plane* and *Flux — GitOps Reconciliation*, alongside three host dashboards. Grafana HTTP health alone does not prove provisioning; verify an **authenticated** dashboard catalog. Anonymous catalog returns 401 and is not a dashboard-loss indication.

If the Flux Ready-condition panels display *No data*, check whether `gotk_resource_info` or other required object-state metrics exist and survive relabeling. Do **not** convert empty data to zero successes/failures. Query current reconciliation state from the Kubernetes control plane with a pre-authorized kubectl identity, not by broadening the observer's read privileges.

## When targets fail

1. Separate host failures (`pi-nodes`) from common API-mediated failures (all three `:6443` targets). Do not assume three failures mean three independent component failures.
2. From the R5C verify host TCP reachability to `10.0.0.5:6443`, local network routing, observer certificate expiry and Prometheus target `lastError`. The `10.96.0.1` VIP and Flux Pod IPs are not required to be reachable from R5C.
3. If TCP is open but TLS/auth fails, verify the public cluster CA and subject/expiry with OpenSSL; use the protected observer kubeconfig for authorized read-only checks. Never disable certificate verification or substitute the administrator kubeconfig in Prometheus.
4. On the control-plane host (`ssh ci-controller-01` with verified host keys), inspect `kubectl get --raw=/readyz`, `kubectl -n flux-system get deploy,svc`, and the explicit metrics-only Services. Prefer diagnostics over changing CRDs/RBAC or restarting control-plane Pods.
5. If Prometheus or Grafana fails to start, inspect systemd journals and their installed storage guards. Confirm `storage_sdcard` is the mounted ext4 filesystem and the configured service bind paths and file permissions are safe; do not bypass the guards.
6. Re-run approved Ansible playbooks only after confirming source checkout and live identity; expect `changed=0` when already converged.

## Certificate renewal and revocation boundary

The observer certificate recorded at G4 expires **2027-01-12 03:15:36 UTC**. Check before that date; reserve an operational rotation window. A 90-day certificate is not an auto-renewal system.

For rotation, do not reuse an unrelated deployer identity: create and verify a new dedicated observer key/CSR (or explicitly approve a key-reuse decision), inspect the requested signer `kubernetes.io/kube-apiserver-client`, subject and usages, require manual cluster-admin authorization to approve **only that CSR**, then **immediately retrieve and persist** the issued certificate. Kubernetes can garbage-collect CSR objects, and one approved request was already lost before capture. Verify CA, key pairing, subject, valid dates, positive/negative RBAC and three job scrapes before moving runtime bindings. Preserve rollback copies securely until acceptance. Removal of RBAC bindings or replacing trust must be planned separately; deleting a CSR is not certificate revocation.

## Boundaries and follow-ups

The initial X.509 allow/deny acceptance covered authorized API/Flux metrics and denied unauthorized resources and mutations. Later G4 confirmed eight UP targets, Ansible idempotence, container identity and budgets, and five provisioned dashboards. It did **not** demonstrate exporter VLAN isolation, real outage recovery, reboot-safe Compose startup, automated credential rotation or complete Kubernetes workload-state monitoring. See [Sprint 14](../sprints/14-kubernetes-flux-telemetry.md) and [roadmap](../roadmap.md) for deferrals.
