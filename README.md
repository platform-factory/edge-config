# edge-config

This repo **will** declare all routing — internal and external — plus the DNS and WAF (Web Application Firewall) configuration that goes with it, because the folder a change lands in is what decides who reviews it: the repo boundary is the approval boundary ([ADR-0001](https://github.com/platform-factory/platform-factory-concept/blob/main/docs/adr/0001-repo-boundary-is-approval-boundary.md)), and putting every route in one place is what makes that boundary reviewable ([ADR-0002](https://github.com/platform-factory/platform-factory-concept/blob/main/docs/adr/0002-all-routes-in-edge-config.md)). **Today it is an empty scaffold**: none of that configuration is here yet; it is **M3** work. What does exist, from commit one, is the boundary in file form: `.github/CODEOWNERS` routes `/external/` to `@platform-factory/security`, before there is anything under that path to change.

## Part of the Platform Factory

This repo is one of seven that make up the reference implementation of the
**Platform Factory** pattern. The design seed — pattern docs, ADRs, and the
build plan — lives at [https://github.com/platform-factory/platform-factory-concept](https://github.com/platform-factory/platform-factory-concept).

Platform Factory was designed and written by **Ronak Patel**
([thecloudgeek LLC](https://github.com/thecloudgeek)). Licensed Apache-2.0 —
the attribution to keep is in [NOTICE](NOTICE), and
[CITATION.cff](CITATION.cff) says how to cite it.

This repo is built out in **M3**.

## Status

**Status:** scaffold — build in progress, following the pre-registered build plan in the design seed repo.
