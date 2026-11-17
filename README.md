# snakemake-methods

Writes a methods section (`methods.md`), a software versions table and a
BibTeX reference list from a Snakemake run. The methods describe only the
steps that were run, cite each tool with its version at its first mention,
list only the cited references and end with the configuration of the run.

- **Package** (`snakemake_methods`): versions, citations, rendering and
  writers, plus a shared database of tools and references
  (`src/snakemake_methods/data/`), each reference checked against the
  publication.
- **Per workflow**: the methods prose as a Jinja2 template, the Snakemake rules
  that collect versions, and a short script. Reference copies are in
  [`workflow/`](workflow/); see [docs/adoption.md](docs/adoption.md).

## Install

In a workflow's `workflow/envs/methods.yaml`:

```yaml
  - pip:
      - git+https://github.com/niekwit/snakemake-methods@v0.1.0
```

## Use

```python
# workflow/scripts/methods.py
from snakemake_methods.snakemake import run

run(snakemake, context={"idr": snakemake.config["idr"]["enable"]})
```

```jinja
{# workflow/methods/methods.md.j2 #}
Peaks were called with {{ tool("macs2", code("-p " ~ config["macs2"]["pval"])) }}
{% if idr %}
and filtered with {{ tool("idr") }}
{% endif %}
.
```

gives "Peaks were called with MACS2 v2.2.9.1 (`-p 0.01`; Zhang et al., 2008)
and filtered with IDR v2.0.4.2 (Li et al., 2011)."

## Development

```bash
conda create -p /mnt/4TB_SSD/conda_envs/snakemake-methods-dev -c conda-forge python=3.12 jinja2 pyyaml pytest pip
/mnt/4TB_SSD/conda_envs/snakemake-methods-dev/bin/pip install -e .
/mnt/4TB_SSD/conda_envs/snakemake-methods-dev/bin/python -m pytest
python tools/verify_references.py   # after adding or changing references
```
