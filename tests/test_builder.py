import pytest

from snakemake_methods import Database, MethodsBuilder, MethodsError, Version


def test_first_mention_has_version_and_citation(builder):
    assert builder.tool("macs2") == "MACS2 v2.2.9.1 (Zhang et al., 2008)"
    assert builder.tool("macs2") == "MACS2"
    assert builder.tool("macs2", "callpeak") == "MACS2 (callpeak)"


def test_detail_on_first_mention(builder):
    assert builder.tool("samtools", "`view -F 1804`") == (
        "SAMtools v1.21 (`view -F 1804`; Danecek et al., 2021)"
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
    assert builder.tool("snakemake") == "Snakemake v9.27.1 (Mölder et al., 2021)"


def test_git_version(builder):
    assert builder.tool("bagel2") == "BAGEL2 commit 1a2b3c4 (Kim & Hart, 2021)"


def test_references_by_version(builder):
    assert builder.tool("string") == "STRING v12.0 (Szklarczyk et al., 2023)"


def test_reference_by_unknown_version_is_a_problem(versions):
    versions["string_db"]["string-db"] = Version("13.0", "api")
    b = MethodsBuilder(versions=versions)
    assert b.tool("string") == "STRING v13.0"
    assert any("No reference" in m for m in b.missing)
    with pytest.raises(MethodsError, match="No reference"):
        MethodsBuilder(versions=versions, strict=True).tool("string")


def test_missing_version_warns_or_raises(builder):
    assert builder.tool("deseq2") == "DESeq2 (Love et al., 2014)"
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
    assert builder.cite("benjamini1995") == "(Benjamini & Hochberg, 1995)"
    assert builder.citation("zhang2008", "amemiya2019") == (
        "Zhang et al., 2008; Amemiya et al., 2019"
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
    assert builder.tool("ashr") == "ashr v2.2-63 (Stephens, 2017)"


def test_package_version(builder):
    assert builder.package_version("python") == "3.12.1"
    assert builder.package_version("python", env="qc") == "3.9.2"
    assert builder.package_version("nope") == ""
    assert builder.cited == []
