"""
Reference and tool databases (data/references.yaml and data/tools.yaml),
shared by all workflows; a workflow can add or change entries (overrides).
"""

import copy
import re
from dataclasses import dataclass, field, fields
from importlib import resources

import yaml

REFERENCE_TYPES = {"article", "inproceedings", "book", "manual", "misc"}


class DatabaseError(ValueError):
    pass


@dataclass
class Reference:
    key: str
    citation: str  # in-text citation without parentheses: "Zhang et al., 2008"
    title: str
    authors: list = field(default_factory=list)
    et_al: bool = False  # author list truncated
    type: str = "article"
    year: str | None = None
    journal: str | None = None
    volume: str | None = None
    pages: str | None = None
    booktitle: str | None = None
    publisher: str | None = None
    doi: str | None = None
    pmid: str | None = None
    url: str | None = None
    note: str | None = None  # appended to the full reference after "; "

    @property
    def link(self):
        return f"https://doi.org/{self.doi}" if self.doi else self.url

    def venue(self):
        if self.type == "article":
            text = self.journal or ""
            if self.volume:
                text += f" {self.volume}"
                if self.pages:
                    text += f":{self.pages}"
            elif self.pages:
                text += f" {self.pages}"
            return text.strip()
        if self.type == "inproceedings":
            return ", ".join(x for x in [self.booktitle, self.pages] if x)
        return self.publisher or ""

    def format(self):
        """
        Full reference: "Zhang Y, Liu T, ... (2008). Model-based analysis of
        ChIP-Seq (MACS). Genome Biol 9:R137. https://doi.org/..."
        """
        text = ", ".join(self.authors)
        if self.et_al:
            text += ", et al."
        if self.year:
            text += f" ({self.year})"
        text += "" if text.endswith(".") else "."
        title = self.title
        text += f" {title}" + ("" if title[-1] in ".?!" else ".")
        venue = self.venue()
        if venue:
            text += f" {venue}."
        if self.link:
            text += f" {self.link}"
        if self.note:
            text += f"; {self.note}"
        return text

    def bibtex(self):
        """BibTeX entry (e.g. for Zotero)"""
        entry_type = {"manual": "manual", "misc": "misc"}.get(self.type, self.type)
        authors = [bibtex_name(a) for a in self.authors]
        if self.et_al:
            authors.append("others")
        values = [
            ("author", " and ".join(authors)),
            ("title", bibtex_escape(self.title)),
            ("journal", self.journal if self.type == "article" else None),
            ("booktitle", self.booktitle),
            ("publisher", self.publisher if self.type != "article" else None),
            ("year", self.year),
            ("volume", self.volume),
            ("pages", self.pages.replace("–", "--") if self.pages else None),
            ("doi", self.doi),
            ("pmid", self.pmid),
            ("url", self.url if self.url else None),
            ("note", bibtex_escape(self.note) if self.note else None),
        ]
        lines = [f"@{entry_type}{{{self.key},"]
        for name, value in values:
            if value:
                lines.append(f"  {name} = {{{value}}},")
        lines.append("}")
        return "\n".join(lines)


def bibtex_name(author):
    """'Zhang Y' -> 'Zhang, Y.', 'Smit AFA' -> 'Smit, A. F. A.'; others in braces"""
    match = re.fullmatch(r"(.+) ([A-Z]{1,4})", author)
    if not match:
        return "{" + bibtex_escape(author) + "}"
    last, initials = match.groups()
    return f"{bibtex_escape(last)}, " + " ".join(f"{i}." for i in initials)


def bibtex_escape(text):
    return re.sub(r"(?<!\\)([&%#_])", r"\\\1", str(text))


@dataclass
class Tool:
    key: str
    name: str  # as written in the text
    references: list = field(default_factory=list)
    # Conda package (or git/API) names to look up the version
    packages: list = field(default_factory=list)
    # Only versions from these environments (None: all)
    envs: list | None = None
    # Reference per version (prefix match), e.g. STRING 12.0
    references_by_version: dict = field(default_factory=dict)

    def references_for(self, version):
        if version:
            for prefix, refs in self.references_by_version.items():
                if str(version).startswith(str(prefix)):
                    return [refs] if isinstance(refs, str) else list(refs)
        return list(self.references)


def _read_yaml(name):
    text = resources.files("snakemake_methods").joinpath("data", name).read_text()
    return yaml.safe_load(text) or {}


def _merge(base, overrides):
    merged = copy.deepcopy(base)
    for key, values in (overrides or {}).items():
        if values is None:
            merged.pop(key, None)
        elif key in merged:
            merged[key].update(values)
        else:
            merged[key] = dict(values)
    return merged


def _build(cls, key, values, kind):
    known = {f.name for f in fields(cls)}
    unknown = set(values) - known
    if unknown:
        raise DatabaseError(f"{kind} {key}: unknown fields {sorted(unknown)}")
    values = dict(values)
    for name in ("year", "volume", "pages", "pmid"):
        if values.get(name) is not None:
            values[name] = str(values[name])
    try:
        return cls(key=key, **values)
    except TypeError as e:
        raise DatabaseError(f"{kind} {key}: {e}") from None


class Database:
    """References and tools, with the overrides of a workflow"""

    def __init__(self, references=None, tools=None, overrides=None):
        overrides = overrides or {}
        references = _merge(
            references if references is not None else _read_yaml("references.yaml"),
            overrides.get("references"),
        )
        tools = _merge(
            tools if tools is not None else _read_yaml("tools.yaml"),
            overrides.get("tools"),
        )
        self.references = {
            k: _build(Reference, k, v, "Reference") for k, v in references.items()
        }
        self.tools = {k: _build(Tool, k, v, "Tool") for k, v in tools.items()}
        self.check()

    def check(self):
        """Raises DatabaseError for incomplete entries or unknown references"""
        errors = []
        citations = {}
        for key, ref in self.references.items():
            if ref.type not in REFERENCE_TYPES:
                errors.append(f"Reference {key}: unknown type {ref.type}")
            if not ref.authors:
                errors.append(f"Reference {key}: no authors")
            if not ref.link:
                errors.append(f"Reference {key}: no DOI or URL")
            if ref.type == "article" and not ref.journal:
                errors.append(f"Reference {key}: article without journal")
            if ref.citation in citations:
                errors.append(
                    f"References {citations[ref.citation]} and {key} have the "
                    f"same citation ({ref.citation})"
                )
            citations[ref.citation] = key
        for key, tool in self.tools.items():
            refs = list(tool.references)
            for value in tool.references_by_version.values():
                refs += [value] if isinstance(value, str) else list(value)
            for ref in refs:
                if ref not in self.references:
                    errors.append(f"Tool {key}: unknown reference {ref}")
        if errors:
            raise DatabaseError("\n".join(errors))

    def tool(self, key):
        try:
            return self.tools[key]
        except KeyError:
            raise KeyError(f"Unknown tool: {key}") from None

    def reference(self, key):
        try:
            return self.references[key]
        except KeyError:
            raise KeyError(f"Unknown reference: {key}") from None


def load_overrides(path):
    """Overrides of a workflow (YAML with 'references' and/or 'tools')"""
    if not path:
        return {}
    with open(path) as fh:
        data = yaml.safe_load(fh) or {}
    unknown = set(data) - {"references", "tools"}
    if unknown:
        raise DatabaseError(f"{path}: unknown sections {sorted(unknown)}")
    return data
