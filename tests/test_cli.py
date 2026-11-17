import os

from snakemake_methods.cli import lint, main, string_db_version, template_calls


def test_template_calls():
    source = (
        "{{ tool('macs2', code('-p')) }} {{ cite('a', 'b') }}\n"
        "{% set x = version('python') %}{{ tool(name) }}"
    )
    assert template_calls(source) == [
        ("tool", ["macs2"], 1),
        ("cite", ["a", "b"], 1),
        ("version", ["python"], 2),
        ("tool", [None], 2),
    ]


def test_lint(db):
    source = (
        "{{ tool('macs2') }} {{ tool('nope') }} {{ cite('zhang2008', 'nope2020') }}"
        "{{ tool(name) }}"
    )
    assert lint(source, db) == [
        "line 1: unknown tool 'nope'",
        "line 1: unknown reference 'nope2020'",
        "line 1: tool() with a non-constant argument",
    ]


def test_main(tmp_path, capsys):
    good = tmp_path / "good.md.j2"
    good.write_text("{{ tool('mytool') }} {{ citation('benjamini1995') }}")
    overrides = tmp_path / "overrides.yaml"
    overrides.write_text(
        "tools:\n  mytool: {name: MyTool, references: [zhang2008], "
        "packages: [mytool]}\n"
    )
    assert main(["lint", str(good), "--overrides", str(overrides)]) == 0
    assert main(["lint", str(good)]) == 1
    assert "unknown tool 'mytool'" in capsys.readouterr().err
    assert main(["check-db"]) == 0


def test_string_db_version(tmp_path):
    out = tmp_path / "pathway_analysis.csv"
    out.write_text("x")
    # 2026-03-04 12:00 local time
    import datetime

    stamp = datetime.datetime(2026, 3, 4, 12, 0).timestamp()
    os.utime(out, (stamp, stamp))
    fetch = lambda url: [{"string_version": "12.0", "stable_address": "x"}]
    assert string_db_version([str(out)], fetch=fetch) == [
        "string-db\t12.0\tapi",
        "string-db-date\t2026-03-04\tapi",
    ]
    assert string_db_version([], fetch=fetch) == ["string-db\t12.0\tapi"]
