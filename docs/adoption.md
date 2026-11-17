# Adopting snakemake-methods in a workflow

A workflow that adopts the package writes, after all its other outputs:

| File | Content |
|---|---|
| `methods/methods.md` | Methods of the steps that were run, tools cited with their version at first mention, the cited references and the configuration of the run |

In the text, references are cited by PubMed ID, else DOI, else URL:
"MACS2 v2.2.9.1 (PubMed ID: 18798982)". The reference list gives the full
references, including the PubMed IDs. For author-year citations ("Zhang et al.,
2008") add `citation_style="author-year"` to the params of the `methods` rule.
| `methods/software_versions.tsv` | `environment`, `package`, `version`, `source` (conda, wrapper, git, api), `cited` (yes for the packages of the tools in the text) |
| `methods/references.bib` | The cited references as BibTeX (e.g. for Zotero) |

The reference files are in this repository under `workflow/`, at the paths
they have in a workflow.

## 1. Copy the files

| From this repository | To the workflow | Changes |
|---|---|---|
| `workflow/rules/methods.smk` | `workflow/rules/methods.smk` | add workflow-specific params to the `methods` rule |
| `workflow/envs/methods.yaml` | `workflow/envs/methods.yaml` | the package tag |
| `workflow/scripts/methods.py` | `workflow/scripts/methods.py` | the context the template needs |
| `workflow/methods/methods.md.j2` | `workflow/methods/methods.md.j2` | write the methods |
| `workflow/methods/tools.yaml` | `workflow/methods/tools.yaml` | workflow overrides (can stay empty) |

Include the rules after all other rules, and add the outputs to the target rule:

```python
include: "rules/methods.smk"


rule all:
    input:
        targets(),
        "methods/methods.md",
```

## 2. Provide the functions

The rules call these functions of the workflow (e.g. in `rules/common.smk`).
Keep them explicit and driven by the configuration: list what this
configuration runs, don't derive it from the DAG.

```python
def methods_envs():
    """Conda environments (workflow/envs/{env}.yaml) used by this configuration"""
    envs = ["qc", "align"]
    if config["deseq2"]["run"]:
        envs.append("deseq2")
    return envs


def methods_wrappers():
    """{name: (wrapper, [packages])} of the Snakemake wrappers used"""
    return {
        "fastqc": ("v5.2.1/bio/fastqc", ["fastqc"]),
        "multiqc": ("v9.18.0/bio/multiqc", ["multiqc"]),
    }


def methods_git():
    """{name: clone directory} of tools cloned at run time"""
    return {"bagel2": "resources/bagel2"} if config["bagel2"]["run"] else {}


def methods_string_db():
    """Output files of the STRING queries ([] if STRING is not used)"""
    return []


def methods_targets():
    """All other targets: the methods describe the finished run"""
    return targets()


def env_packages(env):
    """
    Package names in the dependency lines of workflow/envs/{env}.yaml
    (bioconda::macs2=2.2.9.1=py310h7c593f9_1 -> macs2). Read while the
    workflow is parsed: workflow.source_path() gives a local copy of the file,
    also when the workflow is used as a module (snakedeploy), where
    workflow.basedir is the deployment directory
    """
    names = []
    with open(workflow.source_path(f"../envs/{env}.yaml")) as fh:
        for line in fh:
            match = re.match(r"\s*-\s+(?:[^:\s]+::)?([^=<>!\s#]+)", line)
            if match:
                names.append(match.group(1))
    return names
```

`VERSION` must be defined in the Snakefile (`VERSION = "v1.3.0"`). Don't use
`git describe`: with module deployment it runs in the user's directory.

`env_packages()` runs while the workflow is parsed, in the environment that
runs Snakemake, where this package is not installed. That's why it, and the
rules, live in the workflow.

### Where versions come from

- **Workflow conda envs** (`software_versions`): the packages named in the env
  file, plus `python` and `r-base`, as installed (`$CONDA_PREFIX/conda-meta`).
  Package names in an env file that are not cited (system libraries, fonts)
  are kept in `software_versions.tsv` with `cited = no` but never appear in
  the text.
- **Snakemake wrappers** (`wrapper_versions_{name}`): the rule's `conda:` is
  the wrapper's own `environment.yaml` (and pin file), resolved with the same
  function and `--wrapper-prefix` as the `wrapper:` directive. Snakemake
  hashes environments by content, so this job runs in the environment the
  wrapper job used, also in the workflow's container.
- **git clones** (`git_versions`): `git rev-parse HEAD` of the clone, written
  as "commit 1a2b3c4". Pin clones to a commit
  (`git clone URL {output} && git -C {output} checkout SHA`) so that a
  workflow version always runs the same code.
- **STRING** (`string_db_version`): the version reported by the STRING API and
  the date of the queries (the latest modification time of the STRING
  outputs), as `string-db` and `string-db-date`. Each STRING version is cited
  with the paper that describes it (`references_by_version` in `tools.yaml`
  of the package).
- **Snakemake**: the version running the workflow (`params.snakemake_version`).

## 3. Write the template

`workflow/methods/methods.md.j2` is a Jinja2 template of the methods prose. The
writer adds the title, the generated-on line, the references and the
configuration.

Available in the template:

| Name | Use |
|---|---|
| `tool("key", detail=None)` | First mention: `MACS2 v2.2.9.1 (detail; PubMed ID: 18798982)`; later: `MACS2` or `MACS2 (detail)` |
| `cite("key", ...)` / `citation(...)` | `(DOI: 10.1111/j.2517-6161.1995.tb02031.x)` / without parentheses; several references are separated by `; ` |
| `version("key")` | Version string of a tool |
| `package_version("package")` | Version string of any package in the version files (e.g. `string-db-date`) |
| `code(x)`, `x \| code` | Inline code |
| `join_and(list)`, `list \| join_and` | `a, b and c` |
| `number(n)`, `n \| number` | `10,000` |
| `percent(x)`, `x \| percent` | `50%` |
| `config`, `params`, every param by name, the script's context | Values of the run |

Conventions:

- **Every number and setting comes from `config` or params**, never typed
  into the template.
- **Wrap prose freely.** The lines of a paragraph are joined, and blank lines
  separate paragraphs. Headings, list items and code fences are kept as lines.
- **Put `{% if %}` blocks on their own lines.** Spaces before `, . ; : )` and
  after `(` are removed outside inline code, so
  ```
  Peaks were called
  {% if idr %}
  and filtered with IDR
  {% endif %}
  .
  ```
  gives "Peaks were called." or "Peaks were called and filtered with IDR."
- **First mention is in render order.** A `{% set x = tool(...) %}` counts as
  a mention where it is rendered, not where `x` is used.
- **Statistical methods cite the published method or package** (e.g. DESeq2's
  Wald test, Benjamini–Hochberg), never a description of custom code.

## 4. Tools and references

Tools and references shared by all workflows are in the package
(`src/snakemake_methods/data/tools.yaml` and `references.yaml`). Add a tool
there when another workflow might use it. Every reference is checked against
the publication with `python tools/verify_references.py` (Crossref and
PubMed), and each `CHECK` is resolved by hand. Never add a reference that has
not been checked.

`workflow/methods/tools.yaml` holds overrides for one workflow:

```yaml
tools:
  # Take the Python version from these environments only
  python: {envs: [qc, tss]}
  # A tool used by this workflow only
  mytool: {name: MyTool, references: [doe2024], packages: [mytool]}
references:
  # A note appended to a shared reference
  encode2020: {note: "ENCODE ATAC-seq pipeline v2.2.3: https://github.com/ENCODE-DCC/atac-seq-pipeline"}
```

## 5. Check

```bash
# Every tool and reference named in the template exists
snakemake-methods lint workflow/methods/methods.md.j2 --overrides workflow/methods/tools.yaml

# A tool without a version or reference fails the methods rule instead of a warning
SNAKEMAKE_METHODS_STRICT=1 snakemake --sdm conda --cores 4 --conda-prefix /path/outside/dropbox
```

Run the strict check in the workflow's `.test` runs. A new env (or a new
package tag) changes the env hash, so the workflow's Docker image needs a new
tag at its next release.
