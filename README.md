# edge-config

This repo **will** declare all routing — internal and external — plus the DNS and WAF (Web Application Firewall) configuration that goes with it, because the folder a change lands in is what decides who reviews it: the repo boundary is the approval boundary ([ADR-0001](https://github.com/platform-factory/platform-factory-concept/blob/main/docs/adr/0001-repo-boundary-is-approval-boundary.md)), and putting every route in one place is what makes that boundary reviewable ([ADR-0002](https://github.com/platform-factory/platform-factory-concept/blob/main/docs/adr/0002-all-routes-in-edge-config.md)). **Today it holds the route tree and its check** (below); the DNS and WAF configuration are Terraform in `platform-bootstrap`, not here ([ADR-0021 §5–§7](https://github.com/platform-factory/platform-factory-concept/blob/main/docs/adr/0021-the-approval-boundary-on-the-config-connector-engine.md)). The boundary in file form is `.github/CODEOWNERS`, which routes `/external/` to `@platform-factory/security`; the required-reviewer rule that will enforce it is a ruleset change made by hand and recorded in `platform-factory/.github` ([ADR-0021 §10](https://github.com/platform-factory/platform-factory-concept/blob/main/docs/adr/0021-the-approval-boundary-on-the-config-connector-engine.md)).

## The route tree

A route is one file, `<exposure>/<system>/<route>.yaml`, with `<exposure>` either
`external` or `internal`, and `<system>` a System in
[`systems`](https://github.com/platform-factory/systems) `tenants/`:

```
internal/
└── svc-hello/
    └── hello-internal.yaml   host: hello-internal, service: svc-hello, port: 80
```

`external/` is empty until the required-reviewer rule is live: the first
external route is one of C-13's merges, made under that rule (the M3 readiness
note in the claims register).

The file has four fields: `host`, a label (`^[a-z][a-z0-9-]{0,30}[a-z0-9]$`),
`service`, a Service in the System's namespace, `port`, an integer, and
optionally `path`, a prefix (default `/`). There is **no `exposure` field**: the
folder is the only thing that says how exposed a route is, and the platform
reads it ([ADR-0021 §2](https://github.com/platform-factory/platform-factory-concept/blob/main/docs/adr/0021-the-approval-boundary-on-the-config-connector-engine.md)).
The hostname is `<host>.ref.thecloudgeek.io` for an external route and
`<host>.internal.ref.thecloudgeek.io` for an internal one. A route changes no
DNS: each zone has one wildcard record.

Flipping a route from internal to external is one `git mv` of its file into
`external/<system>/`, which changes nothing in it. That pull request touches
`external/`, so it needs an approval from the `security` team
([ADR-0021 §10](https://github.com/platform-factory/platform-factory-concept/blob/main/docs/adr/0021-the-approval-boundary-on-the-config-connector-engine.md)).
Removing a file removes its route.

`scripts/check_routes.py` runs on every pull request and refuses: a top-level
`exposure`, `system` or `route` key; an unknown key; a file anywhere but
`<exposure>/<system>/<name>.yaml`; a System with no tenant file; a host outside
the grammar; a host used twice anywhere in the repo; two external routes in one
System naming the same Service (GKE attaches one Cloud Armor policy to a
Service); a port that is not an integer. `python3 scripts/check_routes.py
--self-test` first runs the must-fail and must-pass fixtures in
`tests/check-fixtures/`. The same refusals are made again where the platform
renders the file, by `charts/route`'s closed schema in `platform-config`.

## Part of the Platform Factory

This repo is one of seven that make up the reference implementation of the
**Platform Factory** pattern. The design seed — pattern docs, ADRs, and the
build plan — lives at [https://github.com/platform-factory/platform-factory-concept](https://github.com/platform-factory/platform-factory-concept).

Platform Factory was designed and written by **Ronak Patel**
([thecloudgeek LLC](https://github.com/thecloudgeek)). Licensed Apache-2.0 —
the attribution to keep is in [NOTICE](NOTICE), and
[CITATION.cff](CITATION.cff) says how to cite it.

This repo is built out in **M3** (M3a: the tree and the check).

## Status

**Status:** M3a in progress, following the pre-registered build plan in the design seed repo.
