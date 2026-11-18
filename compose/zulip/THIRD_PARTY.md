# Upstream attribution

The dependency configuration in `compose.yaml` is adapted from
[zulip/docker-zulip, tag 13.2-0](https://github.com/zulip/docker-zulip/tree/13.2-0),
licensed under Apache-2.0; the upstream license is included in
`docker-zulip-LICENSE`.

Local changes remove published ports and named volumes, add SD-backed explicit
bind mounts and file credentials, limit resources, use threaded queue workers,
and join only the Caddy proxy, private dependency and application-egress networks.
The overlay is deployed together with `../caddy-public/compose.yaml`.

Images retain their respective upstream licenses. No application or dependency
source code is vendored here.
