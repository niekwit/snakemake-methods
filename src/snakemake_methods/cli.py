"""
snakemake-methods lint TEMPLATE [--overrides FILE]: checks that every tool and
reference named in a methods template exists in the database (with the
workflow's overrides) and that every tool has a reference.

snakemake-methods check-db: checks the database itself.

snakemake-methods string-db-version FILES: version of STRING (online API) and
the date of the queries, as version TSV lines.
"""

import argparse
import datetime
import json
import os
import sys
import urllib.request

import jinja2
from jinja2 import nodes

from .db import Database, DatabaseError, load_overrides

TOOL_FUNCTIONS = {"tool", "version"}
REFERENCE_FUNCTIONS = {"cite", "citation"}


def template_calls(source):
    """
    [(function, [string arguments], line)] of the helper calls in a template;
    non-constant arguments are given as None
    """
    env = jinja2.Environment()
    tree = env.parse(source)
    calls = []
    for call in tree.find_all(nodes.Call):
        if not isinstance(call.node, nodes.Name):
            continue
        name = call.node.name
        if name not in TOOL_FUNCTIONS | REFERENCE_FUNCTIONS:
            continue
        args = [a.value if isinstance(a, nodes.Const) else None for a in call.args]
        # tool(key, detail): only the key is a name
        if name in TOOL_FUNCTIONS:
            args = args[:1]
        calls.append((name, args, call.lineno))
    return calls


def lint(source, db):
    """Problems (strings) of a template"""
    problems = []
    for name, args, line in template_calls(source):
        for arg in args:
            if arg is None:
                problems.append(f"line {line}: {name}() with a non-constant argument")
            elif name in TOOL_FUNCTIONS:
                tool = db.tools.get(arg)
                if tool is None:
                    problems.append(f"line {line}: unknown tool {arg!r}")
                elif not tool.references and not tool.references_by_version:
                    problems.append(f"line {line}: tool {arg!r} has no reference")
                elif not tool.packages:
                    problems.append(f"line {line}: tool {arg!r} has no packages")
            elif arg not in db.references:
                problems.append(f"line {line}: unknown reference {arg!r}")
    return problems


STRING_VERSION_URL = "https://string-db.org/api/json/version"


def string_db_version(files, fetch=None):
    """
    Version lines (package, version, source) of STRING: the version reported
    by the STRING API, and the date of the queries (the latest modification
    time of their output files)
    """
    if fetch is None:

        def fetch(url):
            with urllib.request.urlopen(url, timeout=60) as response:
                return json.load(response)

    version = fetch(STRING_VERSION_URL)[0]["string_version"]
    lines = [f"string-db\t{version}\tapi"]
    if files:
        latest = max(os.path.getmtime(f) for f in files)
        lines.append(
            f"string-db-date\t{datetime.date.fromtimestamp(latest).isoformat()}\tapi"
        )
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(prog="snakemake-methods")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("lint", help="check the tools and references of a template")
    p.add_argument("template")
    p.add_argument("--overrides", help="workflow overrides (YAML)")
    sub.add_parser("check-db", help="check the reference and tool database")
    p = sub.add_parser(
        "string-db-version",
        help="STRING version (API) and query date (latest mtime of FILES), as TSV",
    )
    p.add_argument("files", nargs="*")
    args = parser.parse_args(argv)

    if args.command == "string-db-version":
        print("\n".join(string_db_version(args.files)))
        return 0
    try:
        overrides = load_overrides(getattr(args, "overrides", None))
        db = Database(overrides=overrides)
    except DatabaseError as e:
        print(e, file=sys.stderr)
        return 1
    if args.command == "check-db":
        print(f"{len(db.references)} references, {len(db.tools)} tools: OK")
        return 0
    with open(args.template) as fh:
        problems = lint(fh.read(), db)
    for problem in problems:
        print(f"{args.template}: {problem}", file=sys.stderr)
    if not problems:
        print(f"{args.template}: OK")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
