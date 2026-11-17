from types import SimpleNamespace

import pytest

from snakemake_methods import MethodsError
from snakemake_methods.snakemake import run

TEMPLATE = """\
Data were analysed with the workflow {{ workflow_version }} in {{ tool("snakemake") }}.
Peaks were called with {{ tool("macs2", code("-p " ~ config["macs2"]["p"])) }}
{% if extra_text %}
{{ extra_text }}
{% endif %}
.
"""


def fake_snakemake(tmp_path, template=TEMPLATE, **params):
    versions = tmp_path / "encode.tsv"
    versions.write_text("macs2\t2.2.9.1\npython\t3.10.14\n")
    (tmp_path / "methods.md.j2").write_text(template)
    overrides = tmp_path / "tools.yaml"
    overrides.write_text("tools:\n  macs2: {name: MACS2 callpeak}\n")
    return SimpleNamespace(
        input={"versions": [str(versions)]},
        output={
            "methods": str(tmp_path / "methods.md"),
            "versions": str(tmp_path / "software_versions.tsv"),
            "bibtex": str(tmp_path / "references.bib"),
        },
        params={
            "template": str(tmp_path / "methods.md.j2"),
            "overrides": str(overrides),
            "snakemake_version": "9.27.1",
            "workflow_version": "v1.0.0",
            **params,
        },
        config={"macs2": {"p": 0.01}},
        log=[str(tmp_path / "methods.log")],
    )


def test_run_writes_outputs(tmp_path, monkeypatch):
    monkeypatch.delenv("SNAKEMAKE_METHODS_STRICT", raising=False)
    sm = fake_snakemake(tmp_path)
    run(sm, context={"extra_text": "and IDR"}, today="2026-11-17")
    methods = (tmp_path / "methods.md").read_text()
    assert (
        "Data were analysed with the workflow v1.0.0 in Snakemake v9.27.1 "
        "(Mölder et al., 2021). Peaks were called with MACS2 callpeak v2.2.9.1 "
        "(`-p 0.01`; Zhang et al., 2008) and IDR.\n" in methods
    )
    assert "## Configuration\n\n```yaml\nmacs2: {p: 0.01}\n```\n" in methods
    versions = (tmp_path / "software_versions.tsv").read_text()
    assert "encode\tmacs2\t2.2.9.1\tconda\tyes\n" in versions
    assert "encode\tpython\t3.10.14\tconda\tno\n" in versions
    bib = (tmp_path / "references.bib").read_text()
    assert "@article{molder2021," in bib and "@article{zhang2008," in bib
    assert "Cited 2 references" in (tmp_path / "methods.log").read_text()


def test_strict_from_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("SNAKEMAKE_METHODS_STRICT", "1")
    sm = fake_snakemake(tmp_path, template="{{ tool('deseq2') }}")
    with pytest.raises(MethodsError, match="No version found for DESeq2"):
        run(sm)


def test_missing_version_logged(tmp_path, monkeypatch):
    monkeypatch.delenv("SNAKEMAKE_METHODS_STRICT", raising=False)
    sm = fake_snakemake(tmp_path, template="{{ tool('deseq2') }}")
    builder = run(sm)
    assert builder.missing == ["No version found for DESeq2 (deseq2)"]
    assert "WARNING" in (tmp_path / "methods.log").read_text()
