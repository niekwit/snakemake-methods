import pytest

from snakemake_methods import Database, MethodsBuilder, Version


@pytest.fixture
def versions():
    return {
        "encode": {
            "macs2": Version("2.2.9.1"),
            "python": Version("3.10.14"),
            "samtools": Version("1.21"),
        },
        "qc": {"python": Version("3.9.2"), "picard": Version("3.1.1")},
        "reports": {"python": Version("3.12.1"), "fastqc": Version("0.12.1")},
        "r": {"r-base": Version("4.4.1"), "r-ashr": Version("2.2-63")},
        "git_bagel2": {"bagel2": Version("1a2b3c4d5e6f7a8b9c0d", "git")},
        "string_db": {"string-db": Version("12.0", "api")},
    }


@pytest.fixture
def builder(versions):
    return MethodsBuilder(versions=versions, extra={"snakemake": "9.27.1"})


@pytest.fixture
def db():
    return Database()
