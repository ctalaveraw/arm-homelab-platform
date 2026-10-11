# Host Telemetry — Operation and Troubleshooting

Scope: PLAT-012 physical R5C + three Pi Node Exporters. This runbook does **not** cover Kubernetes/Flux controller metrics or Gotify alert routing.

## Hosts and access

| Target | Access from R5C | Exporter | Purpose |
| --- | --- | --- | --- |
| R5C | local Ansible inventory | 10.0.0.50:9100 | management host |
| ci-controller-01 | `ssh ci-controller-01` | 10.0.0.5:9100 | Pi 4 control plane |
| ci-controller-02 | `ssh ci-controller-02` | 10.0.0.6:9100 | Pi 3 worker |
| ci-controller-04 | `ssh ci-controller-04` | 10.0.0.8:9100 | Pi 3 worker |

These aliases depend on local `~/.ssh/config` and verified `known_hosts`; the public inventory does **not** include SSH private keys. Confirm real SSH host-key fingerprints before first enrollment. Ansible `ping` is a remote Python/SSH connection test, not ICMP.

## Interfaces and controls

- Grafana: `http://10.0.0.50:3300`; provisioned dashboards include *R5C — Host Infrastructure* and *Raspberry Pi — Physical Cluster Nodes*.
- Prometheus: `http://127.0.0.1:9090` on R5C; 30s scrape interval, 48h / 512MB TSDB limits. Grafana queries Prometheus over the observability Compose network.
- R5C exporter: `node-exporter.service`, unprivileged identity, 96 MiB systemd memory cap.
- Pi exporters: `node-exporter.service`, unprivileged identity, 64 MiB systemd memory cap; no Kubernetes cluster credentials.
- All stateful monitoring containers require the correct, guarded `storage_sdcard` ext4 mount. Do **not** bypass systemd storage preflight or enable Docker restart policies to work around unavailable SD state.
- HTTP exporter endpoints have no built-in authentication at present. Allow only trusted management/scrape sources; segmented access remains a verification task.

## Deploy and converge

From the R5C's verified `/srv/platform` feature checkout, with correct trusted local SSH aliases:

```bash
bash scripts/ci/validate.sh
.ci-venv/bin/ansible-playbook -i ansible/inventories/pi-nodes.ini ansible/playbooks/10-pi-exporters.yml
.ci-venv/bin/ansible-playbook -i ansible/inventories/local.ini --ask-become-pass ansible/playbooks/08-grafana.yml ansible/playbooks/07-prometheus.yml
```

A second execution should report `changed=0 failed=0`. No SSH private key, kubeadm admin config, cluster-admin token or production secret is committed to source.

## Positive checks

```bash
curl -fsS http://127.0.0.1:9090/-/ready
curl -fsS http://10.0.0.50:3300/api/health
curl -fsSG --data-urlencode 'query=up{job="pi-nodes"}' http://127.0.0.1:9090/api/v1/query
curl -fsSG --data-urlencode 'query=node_filesystem_avail_bytes{job="r5c",mountpoint="/srv/storage/state",fstype="ext4"}' http://127.0.0.1:9090/api/v1/query
for host in ci-controller-01 ci-controller-02 ci-controller-04; do
  ssh -o BatchMode=yes -o StrictHostKeyChecking=yes "$host" 'systemctl is-active node-exporter kubelet; systemctl show node-exporter -p User -p MemoryCurrent -p MemoryMax'
done
```

Verify the `up` response contains three unique Pi targets with value `1`; mere HTTP 200 is insufficient. Inspect CPU, memory, and filesystem panels for valid nonempty series after multiple scrape intervals.

## Investigate safely

- `up=0` or missing series: first inspect target address/labels and `curl` from R5C to `http://HOST:9100/metrics`, then check `systemctl status node-exporter.service` and `journalctl -u node-exporter.service` on the affected host.
- `node_filesystem_device_error=1` or missing SD series on R5C: inspect `findmnt --kernel --mountpoint /srv/storage/state`, `namei -l /srv/storage/state`, and the service identity's traverse-only ACL; do not grant global read access to the Grafana secret.
- Prometheus/Grafana unavailable: inspect `systemctl status prometheus grafana`, the corresponding journals, expected ext4 mount label and guarded storage checks; do not mutate persistent state while the underlying SD mount is absent.
- A Pi unreachable over SSH: check network/DNS, the expected host-key fingerprint, and SSH transport before attempting any Ansible change; do not disable strict host-key checking.
- Empty short-rate graphs: wait for two or more 30-second scrapes. Avoid interpreting an initial `No data` as a failed collector.

## Rollback / recovery

The bounded native exporter services can be stopped on one Pi at a time using `sudo systemctl stop node-exporter.service` for an approved recovery exercise; kubelet should remain independent. Restoring declared service state is done with the existing Ansible Pi playbook (not with an untracked hand-edited systemd unit). Prometheus/Grafana configuration changes require the management playbooks and matching SD guards. Preserve monitoring history and configuration; do not delete container volumes as an ad hoc repair.

## Open risk and follow-up acceptance

- Independently test firewall/VLAN reachability to every TCP/9100 endpoint from both trusted and untrusted sources; restrict unwanted clients before claiming network isolation.
- Prove scrape-outage detection and restoration, retention/cardinality and resource budgets under load; document reboot/mount recovery.
- Extend metrics to Kubernetes control plane, workloads, Flux reconciliation and management-service dependencies in subsequent PLAT-012 PRs.
- Add deduplicated, recovery-aware runtime alerts to Gotify under PLAT-013.
