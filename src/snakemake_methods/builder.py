"""
MethodsBuilder: cites tools with their version at the first mention and keeps
the list of cited references.
"""

import logging

from .db import Database
from .versions import OTHER, Version, version_key

logger = logging.getLogger(__name__)


class MethodsError(RuntimeError):
    pass


class MethodsBuilder:
    """
    versions: {environment: {package: Version}} (load_versions)
    extra: versions not in an environment, {tool key: version} (e.g. Snakemake)
    db: Database (default: the package database without overrides)
    strict: raise MethodsError for a mentioned tool without version or
        reference, instead of a warning
    """

    def __init__(self, versions=None, extra=None, db=None, strict=False):
        self.versions = versions or {}
        self.extra = {
            k: v if isinstance(v, Version) else Version(str(v), OTHER)
            for k, v in (extra or {}).items()
            if v
        }
        self.db = db or Database()
        self.strict = strict
        self.cited = []  # reference keys in order of first citation
        self.mentioned = []  # tool keys in order of first mention
        self.missing = []  # problems found (tools without version/reference)

    # Versions
    # -----------------------------------------------------
    def candidates(self, key):
        """[(environment, package, Version)] of a tool in the run"""
        tool = self.db.tool(key)
        found = []
        for env, packages in self.versions.items():
            if tool.envs is not None and env not in tool.envs:
                continue
            for package in tool.packages:
                if package in packages:
                    found.append((env, package, packages[package]))
        return found

    def tool_version(self, key):
        """Version of a tool in the run (the latest if there are several)"""
        if key in self.extra:
            return self.extra[key]
        found = [v for _, _, v in self.candidates(key)]
        if not found:
            return None
        return max(found, key=lambda v: version_key(v.version))

    def version(self, key):
        """Version string of a tool ('' if not found)"""
        v = self.tool_version(key)
        return v.version if v else ""

    def package_version(self, package, env=None):
        """
        Version string of a package in the version files, not cited (e.g.
        string-db-date); the latest if it is in several environments
        """
        found = [
            packages[package].version
            for name, packages in self.versions.items()
            if package in packages and env in (None, name)
        ]
        return max(found, key=version_key) if found else ""

    # Citations
    # -----------------------------------------------------
    def citation(self, *keys):
        """In-text citation (without parentheses); adds it to the reference list"""
        for key in keys:
            self.db.reference(key)
            if key not in self.cited:
                self.cited.append(key)
        return "; ".join(self.db.reference(k).citation for k in keys)

    def cite(self, *keys):
        return f"({self.citation(*keys)})"

    def _problem(self, message):
        if self.strict:
            raise MethodsError(message)
        logger.warning(message)
        self.missing.append(message)

    def tool(self, key, detail=None):
        """
        Tool with its version and citation at the first mention, the name
        only after that; detail (e.g. options) goes in the same parentheses:
        "MACS2 v2.2.9.1 (callpeak ...; Zhang et al., 2008)"
        """
        tool = self.db.tool(key)
        if key in self.mentioned:
            return f"{tool.name} ({detail})" if detail else tool.name
        self.mentioned.append(key)
        v = self.tool_version(key)
        if v is None:
            self._problem(f"No version found for {tool.name} ({key})")
        refs = tool.references_for(v.version if v else None)
        if not refs:
            self._problem(f"No reference for {tool.name} ({key})")
        text = f"{tool.name} {v.display()}" if v else tool.name
        inside = "; ".join(
            x for x in [detail, self.citation(*refs) if refs else ""] if x
        )
        return f"{text} ({inside})" if inside else text

    def references(self):
        """Cited references (Reference), sorted as in the reference list"""
        refs = [self.db.reference(k) for k in self.cited]
        return sorted(refs, key=lambda r: r.format().lower().lstrip("("))

    def cited_packages(self):
        """{(environment, package)} of the tools mentioned in the text"""
        cited = set()
        for key in self.mentioned:
            if key in self.extra:
                continue
            cited.update((env, package) for env, package, _ in self.candidates(key))
        return cited
