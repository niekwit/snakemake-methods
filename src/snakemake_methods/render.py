"""
Renders a workflow's methods template (Jinja2) with the builder's helpers.

Prose in a template can be wrapped freely: the lines of a paragraph are joined
with single spaces, and blank lines separate paragraphs. Headings, list items,
table rows and code fences are kept as lines. Outside inline code, runs of
spaces are collapsed and spaces before , . ; : ) and after ( are removed, so
that {% if %} blocks can sit on their own lines.
"""

import os
import re

import jinja2

from . import text as text_helpers

LIST_ITEM = re.compile(r"^\s*([-*+]|\d+\.)\s|^\s*\|")


def environment(builder, searchpath="."):
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(searchpath),
        undefined=jinja2.StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
        keep_trailing_newline=False,
    )
    env.globals.update(
        tool=builder.tool,
        cite=builder.cite,
        citation=builder.citation,
        version=builder.version,
        package_version=builder.package_version,
        code=text_helpers.code,
        join_and=text_helpers.join,
        number=text_helpers.number,
        percent=text_helpers.percent,
    )
    env.filters.update(
        join_and=text_helpers.join,
        number=text_helpers.number,
        percent=text_helpers.percent,
        code=text_helpers.code,
    )
    return env


def render_template(path, builder, **context):
    """Renders a template file and reflows its paragraphs"""
    env = environment(builder, os.path.dirname(os.path.abspath(path)))
    template = env.get_template(os.path.basename(path))
    return reflow(template.render(**context))


def render_string(source, builder, **context):
    env = environment(builder)
    return reflow(env.from_string(source).render(**context))


def tighten(line):
    """Spacing outside inline code (backticks)"""
    parts = line.split("`")
    for i in range(0, len(parts), 2):
        part = re.sub(r"[ \t]+", " ", parts[i])
        part = re.sub(r" +([.,;:)])", r"\1", part)
        part = re.sub(r"\( +", "(", part)
        parts[i] = part
    return "`".join(parts).strip()


def _prose(lines):
    """Lines of a paragraph -> joined lines (list items/table rows kept)"""
    out = []
    for line in lines:
        if LIST_ITEM.match(line) or not out:
            out.append(line.strip())
        else:
            out[-1] += " " + line.strip()
    return "\n".join(tighten(line) for line in out)


def reflow(rendered):
    blocks = []
    current = []
    fence = None

    def flush():
        if current:
            blocks.append(_prose(current))
            current.clear()

    for line in rendered.split("\n"):
        stripped = line.strip()
        if fence is not None:
            fence.append(line.rstrip())
            if stripped.startswith("```"):
                blocks.append("\n".join(fence))
                fence = None
            continue
        if stripped.startswith("```"):
            flush()
            fence = [line.rstrip()]
        elif not stripped:
            flush()
        elif stripped.startswith("#"):
            flush()
            blocks.append(stripped)
        else:
            current.append(line)
    flush()
    if fence is not None:
        blocks.append("\n".join(fence))
    return "\n\n".join(b for b in blocks if b)
