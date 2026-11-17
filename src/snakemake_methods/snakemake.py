"""
The methods rule of a workflow in one call, from its script:

    from snakemake_methods.snakemake import run
    run(snakemake, context={...})

Expected in the rule:
    input.versions   version TSVs (results/software_versions/{name}.tsv)
    output.methods   methods.md
    output.versions  software_versions.tsv
    output.bibtex    references.bib (optional)
    params.template  methods template, as workflow.source_path(...)
    params.overrides workflow overrides of the database (optional, YAML)
    params.snakemake_version (optional)
    params.citation_style "id" (default: PubMed ID, else DOI, else URL) or
                     "author-year"
    log[0]           log file

All params are also available in the template by name, besides config,
params and the context given here. The environment variable
SNAKEMAKE_METHODS_STRICT=1 (or params.strict) fails the rule for a tool
without version or reference.
"""

import logging
import os

from .builder import MethodsBuilder
from .db import Database, load_overrides
from .render import render_template
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

    db = Database(overrides=load_overrides(params.get("overrides")))
    builder = MethodsBuilder(
        versions=versions,
        extra={"snakemake": params.get("snakemake_version")},
        db=db,
        strict=_strict(params),
        style=params.get("citation_style", "id"),
    )
    variables = dict(params)
    variables.update(context or {})
    variables.update(config=config, params=params)
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
