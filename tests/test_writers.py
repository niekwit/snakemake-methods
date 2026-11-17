from snakemake_methods import (
    config_yaml,
    methods_markdown,
    write_bibtex,
    write_versions,
)


def test_methods_markdown(builder):
    body = f"Peaks were called with {builder.tool('macs2')}."
    text = methods_markdown(
        body, builder, config={"macs2": {"pval": 0.01}}, today="2026-11-17"
    )
    assert text == (
        "# Methods\n\n"
        "*Generated on 2026-11-17 from the configuration of the run (appended "
        "below). Software versions are those installed in the conda environments "
        "of the run.*\n\n"
        "Peaks were called with MACS2 v2.2.9.1 (Zhang et al., 2008).\n\n"
        "## References\n\n"
        "- Zhang Y, Liu T, Meyer CA, Eeckhoute J, Johnson DS, Bernstein BE, "
        "Nusbaum C, Myers RM, Brown M, Li W, Liu XS (2008). Model-based analysis "
        "of ChIP-Seq (MACS). Genome Biol 9:R137. "
        "https://doi.org/10.1186/gb-2008-9-9-r137\n\n"
        "## Configuration\n\n```yaml\nmacs2: {pval: 0.01}\n```\n"
    )


def test_custom_preamble_and_no_config(builder):
    text = methods_markdown("Body.", builder, preamble="", title="Methods")
    assert text == "# Methods\n\nBody.\n\n"


def test_config_yaml_plain_types():
    class Config(dict):
        pass

    assert config_yaml(Config(a=Config(b=[1, 2]), c=("x",))) == (
        "a:\n  b: [1, 2]\nc: [x]\n"
    )


def test_write_versions(tmp_path, builder):
    builder.tool("python")
    builder.tool("bagel2")
    path = tmp_path / "software_versions.tsv"
    write_versions(path, builder)
    lines = path.read_text().splitlines()
    assert lines[0] == "environment\tpackage\tversion\tsource\tcited"
    assert "encode\tmacs2\t2.2.9.1\tconda\tno" in lines
    assert "encode\tpython\t3.10.14\tconda\tyes" in lines
    assert "reports\tpython\t3.12.1\tconda\tyes" in lines
    assert "git_bagel2\tbagel2\t1a2b3c4d5e6f7a8b9c0d\tgit\tyes" in lines
    assert "r\tr-ashr\t2.2-63\tconda\tno" in lines


def test_write_bibtex(tmp_path, builder):
    builder.tool("macs2")
    builder.cite("amemiya2019")
    path = tmp_path / "references.bib"
    write_bibtex(path, builder)
    text = path.read_text()
    assert text.index("@article{amemiya2019,") < text.index("@article{zhang2008,")
    assert text.endswith("}\n")
