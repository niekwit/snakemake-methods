from snakemake_methods import Version, load_versions, read_versions, version_key


def test_read_versions_two_and_three_columns(tmp_path):
    path = tmp_path / "encode.tsv"
    path.write_text("macs2\t2.2.9.1\nbagel2\tabc123\tgit\n\nbroken line\n")
    versions = read_versions(path)
    assert versions == {
        "macs2": Version("2.2.9.1", "conda"),
        "bagel2": Version("abc123", "git"),
    }


def test_r_package_underscores(tmp_path):
    path = tmp_path / "r.tsv"
    path.write_text("r-ashr\t2.2_63\nr-base\t4.4_1\nbioconductor-deseq2\t1.42.0\n")
    versions = read_versions(path)
    assert versions["r-ashr"].version == "2.2-63"
    # r-base is not an R package version
    assert versions["r-base"].version == "4.4_1"
    assert versions["bioconductor-deseq2"].version == "1.42.0"


def test_load_versions_named_by_file(tmp_path):
    for name in ("encode", "qc"):
        (tmp_path / f"{name}.tsv").write_text("python\t3.10.14\n")
    versions = load_versions([tmp_path / "encode.tsv", str(tmp_path / "qc.tsv")])
    assert set(versions) == {"encode", "qc"}


def test_version_key_sorts_numerically():
    assert sorted(["3.9.2", "3.10.14", "3.10.2"], key=version_key) == [
        "3.9.2",
        "3.10.2",
        "3.10.14",
    ]
    assert max(["2.2-63", "2.2-9"], key=version_key) == "2.2-63"


def test_display():
    assert Version("2.2.9.1").display() == "v2.2.9.1"
    assert Version("1a2b3c4d5e6f", "git").display() == "commit 1a2b3c4"
    assert Version("12.0", "api").display() == "v12.0"
