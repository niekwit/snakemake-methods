"""
Methods section, software versions table and references of a Snakemake run.
"""

from .builder import MethodsBuilder, MethodsError
from .db import Database, DatabaseError, Reference, Tool, load_overrides
from .render import reflow, render_string, render_template
from .text import code, join, number, percent
from .versions import Version, load_versions, read_versions, version_key
from .writers import (
    config_yaml,
    methods_markdown,
    write_bibtex,
    write_methods,
    write_versions,
)

__version__ = "0.1.1"

__all__ = [
    "Database",
    "DatabaseError",
    "MethodsBuilder",
    "MethodsError",
    "Reference",
    "Tool",
    "Version",
    "code",
    "config_yaml",
    "join",
    "load_overrides",
    "load_versions",
    "methods_markdown",
    "number",
    "percent",
    "read_versions",
    "reflow",
    "render_string",
    "render_template",
    "version_key",
    "write_bibtex",
    "write_methods",
    "write_versions",
]
