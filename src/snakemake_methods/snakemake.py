"""
The methods rule of a workflow in one call, from its script:

    from snakemake_methods.snakemake import run
    run(snakemake, context={...})

Expected in the rule:
    input.versions   version TSVs (results/software_versions/{name}.tsv)
    output.methods   methods.md
    output.versions  software_versions.tsv
    output.bibtex    references.bib (optional)
    params.template_text  the methods template (Jinja2) as text
    params.overrides_text workflow overrides of the database as YAML text
                     (optional)
    (or params.template / params.overrides: paths of these files)
    params.snakemake_version (optional)
    params.citation_style "id" (default: PubMed ID, else DOI, else URL) or
                     "author-year"
    log[0]           log file

Pass the template and overrides as text, read while the workflow is parsed
(open(workflow.source_path(...)).read()): source_path() gives a new
runtime-cache path at every invocation, so a path in params would make
Snakemake rerun the rule every time, while the text changes only when the
files do. This also works when the workflow is used as a module.

All params (but the template and overrides) are also available in the
template by name, besides config,
params and the context given here. The environment variable
SNAKEMAKE_METHODS_STRICT=1 (or params.strict) fails the rule for a tool
without version or reference.
"""

import logging
import os

import yaml

from .builder import MethodsBuilder
from .db import Database, DatabaseError, load_overrides
from .render import render_string, render_template
from .versions import load_versions
from .writers import write_bibtex, write_methods, write_versions


def _items(namedlist):
    """Named items of a Snakemake Namedlist (or a dict)"""
    if isinstance(namedlist, dict):
        return dict(namedlist)
    return {name: namedlist[name] for name in namedlist.keys()}


def _strict(params):
    env = os.environ.get("SNAKEMAKE_METHODS_STRICT", "").lower()
    return env in ("1", "true", "yes") or bool(params.get("strict", False))


def run(snakemake, context=None, preamble=None, title="Methods", today=None):
    """Writes the outputs of the methods rule; returns the builder"""
    if snakemake.log:
        logging.basicConfig(
            format="%(levelname)s:%(asctime)s:%(message)s",
            level=logging.INFO,
            handlers=[logging.FileHandler(snakemake.log[0])],
            force=True,
        )
    params = _items(snakemake.params)
    inputs = _items(snakemake.input)
    outputs = _items(snakemake.output)
    config = snakemake.config

    versions = load_versions(inputs["versions"])
    for name, packages in versions.items():
        logging.info(f"{name}: {len(packages)} packages")

    if params.get("overrides_text"):
        overrides = yaml.safe_load(params["overrides_text"]) or {}
        unknown = set(overrides) - {"references", "tools"}
        if unknown:
            raise DatabaseError(f"overrides: unknown sections {sorted(unknown)}")
    else:
        overrides = load_overrides(params.get("overrides"))
    db = Database(overrides=overrides)
    builder = MethodsBuilder(
        versions=versions,
        extra={"snakemake": params.get("snakemake_version")},
        db=db,
        strict=_strict(params),
        style=params.get("citation_style", "id"),
    )
    sources = ("template", "template_text", "overrides", "overrides_text")
    variables = {k: v for k, v in params.items() if k not in sources}
    variables.update(context or {})
    variables.update(config=config, params=params)
    if params.get("template_text"):
        body = render_string(params["template_text"], builder, **variables)
    else:
        body = render_template(params["template"], builder, **variables)

    write_methods(
        outputs["methods"],
        body,
        builder,
        config=config,
        title=title,
        preamble=preamble,
        today=today,
    )
    write_versions(outputs["versions"], builder)
    if "bibtex" in outputs:
        write_bibtex(outputs["bibtex"], builder)
    logging.info(f"Cited {len(builder.cited)} references")
    for message in builder.missing:
        logging.warning(message)
    return builder
