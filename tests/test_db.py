import re

import pytest

from snakemake_methods import Database, DatabaseError
from snakemake_methods.db import bibtex_name


def test_package_database_is_consistent(db):
    # Database() runs check(); every tool reference exists
    assert len(db.references) > 40
    for tool in db.tools.values():
        assert tool.packages, tool.key
        assert tool.references or tool.references_by_version, tool.key


def test_references_have_link_and_valid_doi(db):
    for ref in db.references.values():
        assert ref.link, ref.key
        if ref.doi:
            assert re.fullmatch(r"10\.\d{4,9}/\S+", ref.doi), ref.key
        if ref.pmid:
            assert ref.pmid.isdigit(), ref.key


def test_citations_are_unique(db):
    citations = [r.citation for r in db.references.values()]
    assert len(citations) == len(set(citations))


def test_format_article(db):
    assert db.reference("zhang2008").format() == (
        "Zhang Y, Liu T, Meyer CA, Eeckhoute J, Johnson DS, Bernstein BE, Nusbaum "
        "C, Myers RM, Brown M, Li W, Liu XS (2008). Model-based analysis of "
        "ChIP-Seq (MACS). Genome Biol 9:R137. "
        "https://doi.org/10.1186/gb-2008-9-9-r137"
    )


def test_format_et_al_and_software(db):
    assert (
        db.reference("dyer2025")
        .format()
        .startswith(
            "Dyer SC, Austine-Orimoloye O, Azov AG, et al. (2025). Ensembl 2025. "
        )
    )
    assert db.reference("kolde").format() == (
        "Kolde R. pheatmap: Pretty Heatmaps. R package. "
        "https://CRAN.R-project.org/package=pheatmap"
    )
    assert db.reference("andrews2010").format() == (
        "Andrews S (2010). FastQC: a quality control tool for high throughput "
        "sequence data. https://www.bioinformatics.babraham.ac.uk/projects/fastqc/"
    )
    assert db.reference("mckinney2010").format() == (
        "McKinney W (2010). Data structures for statistical computing in Python. "
        "Proc 9th Python in Science Conference, 56–61. "
        "https://doi.org/10.25080/Majora-92bf1922-00a"
    )


def test_overrides_merge_and_add():
    db = Database(
        overrides={
            "references": {
                "encode2020": {"note": "ENCODE ATAC-seq pipeline v2.2.3"},
                "mytool2024": {
                    "citation": "Doe, 2024",
                    "authors": ["Doe J"],
                    "year": 2024,
                    "title": "My tool",
                    "type": "misc",
                    "url": "https://example.org",
                },
            },
            "tools": {
                "python": {"envs": ["encode"]},
                "mytool": {
                    "name": "MyTool",
                    "references": ["mytool2024"],
                    "packages": ["mytool"],
                },
            },
        }
    )
    assert (
        db.reference("encode2020")
        .format()
        .endswith("; ENCODE ATAC-seq pipeline v2.2.3")
    )
    assert db.tool("python").envs == ["encode"]
    assert db.tool("python").packages == ["python"]
    assert db.tool("mytool").references == ["mytool2024"]


def test_unknown_reference_of_tool():
    with pytest.raises(DatabaseError, match="unknown reference nope"):
        Database(overrides={"tools": {"x": {"name": "X", "references": ["nope"]}}})


def test_unknown_field():
    with pytest.raises(DatabaseError, match="unknown fields"):
        Database(overrides={"tools": {"macs2": {"verion": "1"}}})


def test_reference_without_link():
    with pytest.raises(DatabaseError, match="no DOI or URL"):
        Database(
            overrides={
                "references": {"x": {"citation": "X", "authors": ["X Y"], "title": "T"}}
            }
        )


def test_bibtex_names():
    assert bibtex_name("Zhang Y") == "Zhang, Y."
    assert bibtex_name("Smit AFA") == "Smit, A. F. A."
    assert bibtex_name("van der Walt SJ") == "van der Walt, S. J."
    assert bibtex_name("R Core Team") == "{R Core Team}"
    assert bibtex_name("ENCODE Project Consortium") == "{ENCODE Project Consortium}"


def test_bibtex_entry(db):
    entry = db.reference("benjamini1995").bibtex()
    assert entry.startswith("@article{benjamini1995,")
    assert "author = {Benjamini, Y. and Hochberg, Y.}," in entry
    assert "pages = {289--300}," in entry
    assert "doi = {10.1111/j.2517-6161.1995.tb02031.x}," in entry
    assert "and others}" in db.reference("dyer2025").bibtex()
