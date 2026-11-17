import jinja2
import pytest

from snakemake_methods import reflow, render_string, render_template
from snakemake_methods.render import tighten


def test_reflow_joins_paragraph_lines():
    text = "## Heading\nFirst line\n  second line.\n\n\n\nNext   paragraph."
    assert reflow(text) == "## Heading\n\nFirst line second line.\n\nNext paragraph."


def test_reflow_keeps_lists_tables_and_fences():
    text = (
        "Intro:\n- item one\n  continued\n- item two\n\n"
        "| a | b |\n|---|---|\n\n"
        "```yaml\nkey:  value\n\n  nested: 1\n```\nAfter."
    )
    assert reflow(text) == (
        "Intro:\n- item one continued\n- item two\n\n"
        "| a | b |\n|---|---|\n\n"
        "```yaml\nkey:  value\n\n  nested: 1\n```\n\nAfter."
    )


def test_tighten_punctuation_outside_code():
    assert tighten("Peaks ( IDR ) were called ,  with  `a  b ,` .") == (
        "Peaks (IDR) were called, with `a  b ,`."
    )


def test_render_string_with_helpers(builder):
    source = """
## Peaks

Peaks were called with {{ tool("macs2", code("-p " ~ p)) }}
{% if idr %}
and filtered with IDR
{% endif %}
.
Samples: {{ ["a", "b", "c"] | join_and }}; {{ 10000 | number }} reads; {{ 0.5 | percent }}.
"""
    text = render_string(source, builder, p=0.01, idr=False)
    assert text == (
        "## Peaks\n\n"
        "Peaks were called with MACS2 v2.2.9.1 (`-p 0.01`; Zhang et al., 2008). "
        "Samples: a, b and c; 10,000 reads; 50%."
    )


def test_undefined_variable_fails(builder):
    with pytest.raises(jinja2.UndefinedError):
        render_string("{{ missing }}", builder)


def test_render_template_file_with_include(tmp_path, builder):
    (tmp_path / "part.md.j2").write_text("Aligned with {{ tool('samtools') }}.\n")
    (tmp_path / "methods.md.j2").write_text(
        "Intro {{ tool('samtools') }}.\n\n{% include 'part.md.j2' %}"
    )
    text = render_template(str(tmp_path / "methods.md.j2"), builder)
    # First mention in render order
    assert text == (
        "Intro SAMtools v1.21 (Danecek et al., 2021).\n\nAligned with SAMtools."
    )
