"""
Methods section of the run (snakemake-methods). The prose is in
workflow/methods/methods.md.j2; this script only gathers the values the
template needs that are not params of the rule.
"""

from snakemake_methods.snakemake import run

config = snakemake.config

# Values derived from the configuration, available in the template by name
context = {
    # "idr": config["idr"]["enable"],
}

run(snakemake, context=context)
