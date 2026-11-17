"""
Software versions of a run, from the TSV files written by the versions rules
(results/software_versions/{name}.tsv: package, version and optionally the
source of the version, without a header).
"""

import os
import re
from dataclasses import dataclass

# Sources of versions
CONDA = "conda"  # conda environment of the workflow (conda-meta)
WRAPPER = "wrapper"  # conda environment of a Snakemake wrapper (conda-meta)
GIT = "git"  # commit of a git clone
API = "api"  # version reported by an online service
OTHER = "other"  # given directly (e.g. Snakemake itself)


@dataclass(frozen=True)
class Version:
    version: str
    source: str = CONDA

    def display(self):
        """'v2.2.9.1', or 'commit 1a2b3c4' for git commits"""
        if self.source == GIT:
            return f"commit {self.version[:7]}"
        return f"v{self.version}"


def normalise(package, version):
    """
    conda writes the "-" of R package versions as "_" (ashr 2.2-63 is
    2.2_63); gives the version as R reports it
    """
    if package.startswith("r-") and package != "r-base":
        return version.replace("_", "-")
    return version


def version_key(version):
    """Sort key for versions (3.10.14 after 3.9.2)"""
    return [
        (0, int(x), "") if x.isdigit() else (1, 0, x)
        for x in re.split(r"[.\-_]", version)
    ]


def read_versions(path, default_source=CONDA):
    """{package: Version} of one TSV file"""
    versions = {}
    with open(path) as fh:
        for line in fh:
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 2 or not fields[0]:
                continue
            package, version = fields[0], fields[1]
            source = fields[2] if len(fields) > 2 and fields[2] else default_source
            versions[package] = Version(normalise(package, version), source)
    return versions


def load_versions(paths, default_source=CONDA):
    """
    {name: {package: Version}} of TSV files, with the file name (without
    .tsv) as the name of the environment
    """
    versions = {}
    for path in paths:
        name = os.path.basename(str(path)).removesuffix(".tsv")
        versions[name] = read_versions(path, default_source)
    return versions
