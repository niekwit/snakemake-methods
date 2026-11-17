import pytest

from snakemake_methods import Database, MethodsBuilder, MethodsError, Version


def test_first_mention_has_version_and_citation(builder):
    assert builder.tool("macs2") == "MACS2 v2.2.9.1 (PubMed ID: 18798982)"
    assert builder.tool("macs2") == "MACS2"
    assert builder.tool("macs2", "callpeak") == "MACS2 (callpeak)"


def test_detail_on_first_mention(builder):
    assert builder.tool("samtools", "`view -F 1804`") == (
        "SAMtools v1.21 (`view -F 1804`; PubMed ID: 33590861)"
    )


def test_latest_version_over_environments(builder):
    assert builder.version("python") == "3.12.1"


def test_envs_restriction(versions):
    db = Database(overrides={"tools": {"python": {"envs": ["encode", "qc"]}}})
    b = MethodsBuilder(versions=versions, db=db)
    assert b.version("python") == "3.10.14"
    assert b.cited_packages() == set()
    b.tool("python")
    assert b.cited_packages() == {("encode", "python"), ("qc", "python")}


def test_extra_versions(builder):
    assert (
        builder.tool("snakemake")
        == "Snakemake v9.27.1 (DOI: 10.12688/f1000research.29032.2)"
    )


def test_git_version(builder):
    assert builder.tool("bagel2") == "BAGEL2 commit 1a2b3c4 (PubMed ID: 33407829)"


def test_references_by_version(builder):
    assert builder.tool("string") == "STRING v12.0 (PubMed ID: 36370105)"


def test_reference_by_unknown_version_is_a_problem(versions):
    versions["string_db"]["string-db"] = Version("13.0", "api")
    b = MethodsBuilder(versions=versions)
    assert b.tool("string") == "STRING v13.0"
    assert any("No reference" in m for m in b.missing)
    with pytest.raises(MethodsError, match="No reference"):
        MethodsBuilder(versions=versions, strict=True).tool("string")


def test_missing_version_warns_or_raises(builder):
    assert builder.tool("deseq2") == "DESeq2 (PubMed ID: 25516281)"
    assert builder.missing == ["No version found for DESeq2 (deseq2)"]
    strict = MethodsBuilder(versions={}, strict=True)
    with pytest.raises(MethodsError, match="No version found for DESeq2"):
        strict.tool("deseq2")


def test_unknown_tool_and_reference(builder):
    with pytest.raises(KeyError, match="Unknown tool"):
        builder.tool("nope")
    with pytest.raises(KeyError, match="Unknown reference"):
        builder.cite("nope")


def test_cite_and_reference_list(builder):
    assert builder.cite("benjamini1995") == (
        "(DOI: 10.1111/j.2517-6161.1995.tb02031.x)"
    )
    assert builder.citation("zhang2008", "amemiya2019") == (
        "PubMed ID: 18798982; PubMed ID: 31249361"
    )
    builder.cite("benjamini1995")
    assert builder.cited == ["benjamini1995", "zhang2008", "amemiya2019"]
    # Sorted by the full reference, case-insensitive
    assert [r.key for r in builder.references()] == [
        "amemiya2019",
        "benjamini1995",
        "zhang2008",
    ]


def test_r_version_from_r_package(builder):
    assert builder.tool("ashr") == "ashr v2.2-63 (PubMed ID: 27756721)"


def test_package_version(builder):
    assert builder.package_version("python") == "3.12.1"
    assert builder.package_version("python", env="qc") == "3.9.2"
    assert builder.package_version("nope") == ""
    assert builder.cited == []


def test_in_text_falls_back_to_doi_then_url(builder):
    # No PubMed ID: DOI; no DOI: URL
    assert builder.citation("martin2011") == "DOI: 10.14806/ej.17.1.200"
    assert builder.citation("kolde") == "https://CRAN.R-project.org/package=pheatmap"


def test_author_year_style(versions):
    b = MethodsBuilder(versions=versions, style="author-year")
    assert b.tool("macs2") == "MACS2 v2.2.9.1 (Zhang et al., 2008)"
    assert b.cite("benjamini1995") == "(Benjamini & Hochberg, 1995)"


def test_unknown_style():
    with pytest.raises(ValueError, match="Unknown citation style"):
        MethodsBuilder(style="numeric")
