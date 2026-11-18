# Domain and HTTPS Ingress

Status: Caddy configuration prepared; DNS, router policy and certificates not yet accepted.

## Placement

Run Caddy on `gitops-controller-01` for this deployment. It already hosts Forgejo under Ansible/systemd, remains outside Kubernetes, and can own certificate storage without adding application services to the routers.

| System | Change |
| --- | --- |
| DNS provider | Point the chosen public hostname to the reachable home address; use DDNS if that address changes |
| OUTER | Permit/forward only the chosen inbound web ports |
| INNER | Route and permit those connections to the controller; answer LAN split DNS |
| Controller | Caddy listens on its LAN IPv4 TCP/80 and TCP/443 |
| Forgejo | Advertise the HTTPS root URL; trust only Caddy's fixed container IP |

No router rules are generated without current interface, route, zone and NAT information. The routers' installed repositories do not contain those live rules.

## Choose the access model

| Access model | DNS and certificate requirement |
| --- | --- |
| Public HTTPS | Public A record points to a reachable public home address; inbound TCP/80 and TCP/443 reach Caddy; supplied Caddyfile uses automatic ACME |
| LAN/WireGuard only with public trust | INNER DNS resolves the registered hostname internally; DNS-01 certificate issuance needs the DNS provider's Caddy module and a scoped DNS credential |
| LAN test with a private CA | Caddy `tls internal` and client trust installation; this is a different profile from the checked-in public ACME config |

Registering a domain alone does not make an unreachable home network public. If OUTER is behind CGNAT, a public IPv4 inbound path requires an ISP/public-address change or a separately designed relay. DNS-01 can issue certificates for private services but does not create connectivity.

The supplied configuration publishes IPv4 TCP only. Do not add a public AAAA record until IPv6 listening, routing and firewall behavior have been implemented and tested. WireGuard on **UDP**/443 can coexist with HTTPS on **TCP**/443; an existing TCP listener on the same address cannot.

## Router path

Use a public hostname such as `git.<domain>`. The domain can remain stable if the forge implementation changes again.

For routed transit, OUTER can DNAT directly to the controller if it has a route to the controller LAN and INNER permits the forwarded path. If INNER also NATs its downstream LAN, the path may instead require OUTER → INNER transit address and an INNER → controller port forward. Determine which model is actually deployed before editing either firewall; do not add two layers of forwarding by assumption. Account for any upstream ISP router as well.

For LAN/WireGuard clients, configure INNER's DNS to answer the same hostname with the controller LAN address. This avoids dependence on NAT loopback. Ensure those clients actually use the intended DNS resolver.

Forward only the selected web ports. Leave management SSH, LuCI, Kubernetes APIs, Docker, metrics, cache and application backend ports off the public path. Git-over-HTTPS works through Caddy; Git SSH remains a separate LAN/WireGuard service unless separately designed.

## Prepare and activate the public profile

Complete Forgejo initialization and migration acceptance first. Confirm no controller listener already owns TCP/80 or TCP/443 and that the candidate ingress subnet does not overlap host/LAN/VPN/Docker routes.

```bash
ss -lntp
ip -4 route
docker network ls
cp compose/caddy/.env.example compose/caddy/.env
chmod 600 compose/caddy/.env
```

Set the final hostname, ACME contact email and controller LAN bind IP in Caddy's `.env`. Use the same `PROXY_CONTAINER_IP` as Forgejo. Set these values in Forgejo's `.env`:

```text
FORGEJO_FQDN=git.your-domain.tld
FORGEJO_ROOT_URL=https://git.your-domain.tld/
FORGEJO_BIND_IP=127.0.0.1
```

Keep `FORGEJO_SSH_BIND_IP` on the LAN and the advertised SSH port consistent with its host mapping. Apply reviewed DNS/router policy for the selected access model. Then recreate Forgejo and start Caddy:

```bash
sudo systemctl stop forgejo-runner.service
sudo systemctl restart forgejo.service
ansible-playbook ansible/playbooks/11-caddy.yml --ask-become-pass
sudo systemctl start forgejo-runner.service
```

If a runner has not yet been installed, omit its stop/start commands. If Caddy already runs, stop it before restarting Forgejo and start it afterwards: it depends on the Forgejo-owned ingress network. Running `02-forgejo.yml` again with `state: started` alone does not update a running container.

Caddy stores certificates and account keys under the guarded SD-backed `services/caddy/data`. Back it up as private application state. The Docker socket and Caddy administration port are not published.

## Verify

From a LAN client, then separately over cellular:

```bash
curl --fail --head http://git.your-domain.tld/
curl --fail --head https://git.your-domain.tld/
curl --fail https://git.your-domain.tld/api/v1/version
```

Expect an HTTP-to-HTTPS redirect, a trusted hostname-matching certificate, and the expected Forgejo version. A sign-in redirect is normal with anonymous viewing disabled. Do not use `curl -k` as certificate acceptance.

Test authenticated Git clone/fetch and OCI login/retrieval through HTTPS. Verify generated links use the final HTTPS URL with no `:3001`, no mixed content, and correct SSH host/port. Confirm Forgejo sees the intended client address through Caddy. From outside, confirm no backend/administrative ports were exposed by the router change. Test WireGuard/LAN name resolution separately from public DNS.

Check `systemctl status forgejo caddy` and `docker-compose --env-file compose/caddy/.env -f compose/caddy/compose.yml logs --tail 100` for DNS, ACME or upstream errors. Do not post private tokens or full unreviewed configs.

Update Kuma only after the new endpoint is accepted. Wider management HTTPS and a dedicated ingress host remain separate work.

## Rollback

Stop Caddy, restore the previous Forgejo root URL and HTTP bind address, restart Forgejo, then restore prior DNS/client endpoints and remove only the router rules added for this route. Keep certificate state and the old Gitea checkpoint. Reconcile new writes before any fallback to Gitea.

## References

- [Caddy automatic HTTPS and ACME challenges](https://caddyserver.com/docs/automatic-https)
- [Forgejo reverse proxy](https://forgejo.org/docs/v15.0/admin/setup/reverse-proxy/)
- [Forgejo Docker configuration and proxy trust](https://forgejo.org/docs/v15.0/admin/installation/docker/)
