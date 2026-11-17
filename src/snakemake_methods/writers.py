"""Writers of methods.md, software_versions.tsv and references.bib"""

from datetime import date

import yaml

DEFAULT_PREAMBLE = (
    "*Generated on {date} from the configuration of the run (appended below). "
    "Software versions are those installed in the conda environments of the run.*"
)


def config_yaml(config):
    """Configuration of the run (including command line overrides) as YAML"""
    return yaml.safe_dump(
        _plain(config), sort_keys=False, default_flow_style=None, width=88
    )


def _plain(value):
    """Snakemake config objects -> plain dicts/lists for YAML"""
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def methods_markdown(
    body, builder, config=None, title="Methods", preamble=None, today=None
):
    """Methods section: title, preamble, body, references and configuration"""
    today = today or date.today().isoformat()
    preamble = (DEFAULT_PREAMBLE if preamble is None else preamble).format(date=today)
    text = f"# {title}\n\n"
    if preamble:
        text += preamble + "\n\n"
    text += body + "\n\n"
    references = builder.references()
    if references:
        text += "## References\n\n"
        text += "\n".join(f"- {r.format()}" for r in references) + "\n\n"
    if config is not None:
        text += "## Configuration\n\n```yaml\n" + config_yaml(config) + "```\n"
    return text


def write_methods(path, body, builder, **kwargs):
    with open(path, "w") as fh:
        fh.write(methods_markdown(body, builder, **kwargs))


def write_versions(path, builder):
    """
    Versions of all environments in one table: environment, package, version,
    source, cited (yes for packages of the tools mentioned in the text)
    """
    cited = builder.cited_packages()
    with open(path, "w") as fh:
        fh.write("environment\tpackage\tversion\tsource\tcited\n")
        for env in sorted(builder.versions):
            for package in sorted(builder.versions[env]):
                v = builder.versions[env][package]
                flag = "yes" if (env, package) in cited else "no"
                fh.write(f"{env}\t{package}\t{v.version}\t{v.source}\t{flag}\n")


def write_bibtex(path, builder):
    """Cited references as BibTeX (e.g. for Zotero)"""
    refs = sorted(builder.references(), key=lambda r: r.key)
    with open(path, "w") as fh:
        fh.write("\n\n".join(r.bibtex() for r in refs) + ("\n" if refs else ""))
