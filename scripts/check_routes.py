#!/usr/bin/env python3
"""The edge-config repo's check: the route files, and where they sit.

Why it exists
-------------
Every file under external/ or internal/ becomes a route (ADR-0021 §2). The
platform renders it: the folder says how exposed the route is, and a closed
schema in platform-config's charts/route refuses any key but four. This check
runs the same refusals on the pull request, before merge, and adds the ones a
schema cannot see because they compare files: a host used twice, a System that
has no tenant file, two external routes for one Service. The two are meant to
overlap. A case that both accept is an escape (C-10).

There is no `exposure` field. A file that carries one, in either folder, is the
case ADR-0002's folder-to-field check used to catch, and is refused now
because the platform writes `exposure` from the folder and the file may not
(ADR-0021 §2).

This check is advisory until it has failed once and passed once on a real pull
request; then it becomes a required status check (ADR-0019 §4, ADR-0021 §10).

The rules, each with the id it reports
--------------------------------------
  [layout]       a route file is exactly <exposure>/<system>/<name>.yaml, with
                 <exposure> external or internal: no file directly in a
                 folder, none deeper, no .yml, and no YAML file outside
                 .github/, scripts/ and tests/. Argo CD's glob would match a
                 deeper file and name the wrong System; a .yml would be
                 ignored in silence.
  [one-document] each route file is exactly one YAML mapping.
  [platform-key] the file has no top-level `exposure`, `system` or `route`:
                 the platform writes those from the folder.
  [unknown-key]  its keys are host, service, port and optionally path.
  [required]     host, service and port are present.
  [name]         the file's name (without .yaml) follows the host grammar,
                 because it becomes part of an Application and an HTTPRoute
                 name.
  [system]       the folder names a System in platform-factory/systems'
                 tenants/.
  [host]         host matches ^[a-z][a-z0-9-]{0,30}[a-z0-9]$.
  [service]      service is a DNS label.
  [port]         port is an integer from 1 to 65535 (not 80.5, not "80").
  [path]         path, if present, is a prefix: it starts with / .
  [host-unique]  no host appears twice anywhere in the repo, in either folder.
  [service-unique]  no two external routes in one System name the same
                 service: GKE attaches one GCPBackendPolicy to a Service
                 (ADR-0021 §7).

How to run it
-------------
  python3 scripts/check_routes.py --systems ../systems   # check this repo
  python3 scripts/check_routes.py --self-test            # run the fixtures in
                                                         # tests/check-fixtures/
"""

import argparse
import pathlib
import re
import sys

import yaml

EXPOSURES = ("external", "internal")
# Folders that hold no route. Every other YAML file in the repo is refused, so
# a route filed in the wrong place cannot go unread.
NON_ROUTE_DIRS = {".git", ".github", "scripts", "tests"}
HOST_PATTERN = re.compile(r"^[a-z][a-z0-9-]{0,30}[a-z0-9]$")
SERVICE_PATTERN = re.compile(r"^[a-z]([a-z0-9-]{0,61}[a-z0-9])?$")
PATH_PATTERN = re.compile(r"^/[A-Za-z0-9._~/-]*$")
KEYS = {"host", "service", "port", "path"}
REQUIRED = ["host", "service", "port"]
PLATFORM_KEYS = {"exposure", "system", "route"}

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "tests" / "check-fixtures"


def tenant_names(systems):
    """The System names in a checkout of platform-factory/systems."""
    return {p.stem for p in (systems / "tenants").glob("*.yaml")}


def check_repo(repo, tenants):
    """Check one checkout. Returns a list of (rule, message); empty means it passes.

    `tenants` is the set of System names that have a tenant file.
    """
    problems = []
    routes = []  # (exposure, system, name, parsed mapping)
    for path in sorted(repo.rglob("*")):
        parts = path.relative_to(repo).parts
        if not path.is_file() or parts[0] in NON_ROUTE_DIRS or path.suffix not in {".yaml", ".yml"}:
            continue
        where = "/".join(parts)
        if parts[0] not in EXPOSURES:
            problems.append(("layout", f"{where}: a route file belongs in external/<system>/ or internal/<system>/; no other folder holds YAML"))
            continue
        if len(parts) != 3 or path.suffix != ".yaml":
            problems.append((
                "layout",
                f"{where}: a route file is exactly {parts[0]}/<system>/<name>.yaml (no file directly in {parts[0]}/, none deeper, no .yml)",
            ))
            continue
        exposure, system, filename = parts
        name = path.stem
        mapping, file_problems = read_route(path, where)
        problems += file_problems
        if not HOST_PATTERN.match(name):
            problems.append(("name", f"{where}: the file name {name!r} must follow the host grammar ^[a-z][a-z0-9-]{{0,30}}[a-z0-9]$"))
        if system not in tenants:
            problems.append(("system", f"{where}: {system!r} has no tenant file in platform-factory/systems tenants/"))
        if mapping is not None:
            problems += check_route(mapping, where)
            routes.append((exposure, system, name, mapping, where))

    problems += check_uniqueness(routes)
    return problems


def read_route(path, where):
    try:
        documents = [d for d in yaml.safe_load_all(path.read_text()) if d is not None]
    except yaml.YAMLError as error:
        return None, [("one-document", f"{where}: does not parse as YAML: {error}")]
    if len(documents) != 1 or not isinstance(documents[0], dict):
        return None, [("one-document", f"{where}: must hold exactly one YAML mapping, found {len(documents)} document(s)")]
    return documents[0], []


def check_route(route, where):
    """Check the fields of one route file."""
    problems = []
    keys = {str(key) for key in route}
    for key in sorted(keys & PLATFORM_KEYS):
        problems.append((
            "platform-key",
            f"{where}: {key} is not a route field. The platform writes it from the folder the file sits in, "
            "so a file cannot set it (ADR-0021 §2); to change exposure, move the file.",
        ))
    for key in sorted(keys - KEYS - PLATFORM_KEYS):
        problems.append(("unknown-key", f"{where}: {key} is not a route field; the fields are host, service, port and path"))
    for key in REQUIRED:
        if key not in route:
            problems.append(("required", f"{where}: {key} is required"))

    host = route.get("host")
    if "host" in route and not (isinstance(host, str) and HOST_PATTERN.match(host)):
        problems.append(("host", f"{where}: host {host!r} must match ^[a-z][a-z0-9-]{{0,30}}[a-z0-9]$ (a label, 2-32 characters, no dot)"))
    service = route.get("service")
    if "service" in route and not (isinstance(service, str) and SERVICE_PATTERN.match(service)):
        problems.append(("service", f"{where}: service {service!r} must be a Service name in the System's namespace (a DNS label)"))
    port = route.get("port")
    # bool is an int in Python; YAML `true` is not a port.
    if "port" in route and not (isinstance(port, int) and not isinstance(port, bool) and 1 <= port <= 65535):
        problems.append(("port", f"{where}: port {port!r} must be an integer from 1 to 65535"))
    if "path" in route:
        path = route["path"]
        if not (isinstance(path, str) and len(path) <= 128 and PATH_PATTERN.match(path)):
            problems.append(("path", f"{where}: path {path!r} must be a prefix starting with /"))
    return problems


def check_uniqueness(routes):
    problems = []
    seen_host = {}
    seen_service = {}
    for exposure, system, name, route, where in routes:
        host = route.get("host")
        if isinstance(host, str):
            if host in seen_host:
                problems.append((
                    "host-unique",
                    f"{where}: host {host!r} is already used by {seen_host[host]}. A host may appear once in the repo, "
                    "in either folder: the public wildcard also answers names under the internal zone (ADR-0021, Consequences).",
                ))
            else:
                seen_host[host] = where
        service = route.get("service")
        if exposure == "external" and isinstance(service, str):
            key = (system, service)
            if key in seen_service:
                problems.append((
                    "service-unique",
                    f"{where}: service {service!r} is already named by external route {seen_service[key]}. "
                    "GKE attaches one GCPBackendPolicy to a Service (ADR-0021 §7).",
                ))
            else:
                seen_service[key] = where
    return problems


def self_test():
    """Run every fixture. Returns True if each behaved as expected.

    A check that has never been seen to fail is not evidence (ADR-0019 §4), so
    every must-fail fixture has to be refused, and by the rule its `expect`
    file names. The must-pass fixtures prove the rules do not refuse
    everything. All use the System names in tests/check-fixtures/tenants/.
    """
    tenants = tenant_names(FIXTURES)
    all_ok = True
    for kind in ("must-fail", "must-pass"):
        cases = sorted(p for p in (FIXTURES / kind).iterdir() if p.is_dir())
        if not cases:
            print(f"FAIL no {kind} fixtures found under {FIXTURES / kind}")
            all_ok = False
        for case in cases:
            rules = {rule for rule, _ in check_repo(case / "head", tenants)}
            if kind == "must-fail":
                expected = (case / "expect").read_text().strip()
                if expected in rules:
                    print(f"ok   must-fail/{case.name}: refused by [{expected}]")
                else:
                    found = ", ".join(sorted(rules)) or "nothing; it passed"
                    print(f"FAIL must-fail/{case.name}: expected [{expected}], got {found}")
                    all_ok = False
            else:
                if not rules:
                    print(f"ok   must-pass/{case.name}: passed")
                else:
                    print(f"FAIL must-pass/{case.name}: refused by {', '.join(sorted(rules))}")
                    all_ok = False
    return all_ok


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--systems", type=pathlib.Path, help="a checkout of platform-factory/systems")
    parser.add_argument("--self-test", action="store_true", help="run the fixtures instead of checking the repo")
    args = parser.parse_args()

    if args.self_test:
        sys.exit(0 if self_test() else 1)
    if args.systems is None:
        parser.error("--systems is required unless --self-test is given")

    problems = check_repo(REPO_ROOT, tenant_names(args.systems))
    for rule, message in problems:
        # GitHub shows ::error lines as annotations on the pull request.
        print(f"::error::[{rule}] {message}")
    if not problems:
        print("ok   every route file passes")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
