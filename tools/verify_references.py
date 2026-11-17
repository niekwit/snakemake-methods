"""
Checks the DOI references of references.yaml against Crossref (title, year,
volume, pages, authors and initials) and PubMed (PMID by DOI). Prints OK or
CHECK per reference; every CHECK must be resolved by hand against the paper
(PubMed or the publisher) before a reference is added or changed.

Usage: python tools/verify_references.py [src/snakemake_methods/data/references.yaml]
"""

import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

import yaml

UA = {"User-Agent": "snakemake-methods-reference-check/0.1"}


def get(url):
    for i in range(3):
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=UA), timeout=30
            ) as r:
                return json.load(r)
        except Exception as e:
            err = e
            time.sleep(2)
    raise err


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


path = (
    sys.argv[1] if len(sys.argv) > 1 else "src/snakemake_methods/data/references.yaml"
)
refs = yaml.safe_load(open(path))
out = {}
for key, r in refs.items():
    if not r.get("doi"):
        continue
    doi = r["doi"]
    try:
        m = get("https://api.crossref.org/works/" + urllib.parse.quote(doi))["message"]
    except Exception as e:
        print(f"{key}: CROSSREF FAIL {e}")
        continue
    issues = []
    title = (m.get("title") or [""])[0]
    if norm(title) != norm(r["title"]):
        issues.append(f"title: crossref={title!r}")
    year = None
    for f in ("published-print", "issued", "published-online"):
        if m.get(f, {}).get("date-parts"):
            year = m[f]["date-parts"][0][0]
            break
    yrs = {
        m.get(f, {}).get("date-parts", [[None]])[0][0]
        for f in ("published-print", "published-online", "issued")
    }
    if str(r.get("year")) not in {str(y) for y in yrs}:
        issues.append(f"year: crossref={sorted(y for y in yrs if y)}")
    if r.get("volume") and str(m.get("volume")) != str(r["volume"]):
        issues.append(f"volume: crossref={m.get('volume')}")
    page = m.get("page") or m.get("article-number")
    mine = str(r.get("pages", "")).replace("–", "-")
    if page and norm(page) != norm(mine):
        issues.append(
            f"pages: crossref={page} article-number={m.get('article-number')}"
        )
    if not page:
        issues.append(
            f"pages: crossref none (article-number={m.get('article-number')})"
        )
    fams = [a.get("family") or a.get("name", "") for a in m.get("author", [])]
    mine_fam = [re.sub(r" [A-Z]{1,4}$", "", a) for a in r["authors"]]
    if not r.get("et_al") and len(fams) != len(mine_fam):
        issues.append(f"n authors: crossref={len(fams)} mine={len(mine_fam)}")
    for i, (a, b) in enumerate(zip(mine_fam, fams)):
        if norm(a) != norm(b):
            issues.append(f"author {i+1}: mine={a!r} crossref={b!r}")
    # initials
    inits = []
    for a in m.get("author", []):
        g = a.get("given", "")
        inits.append("".join(w[0] for w in re.split(r"[\s.\-]+", g) if w).upper())
    for i, (a, ini) in enumerate(zip(r["authors"], inits)):
        mm = re.fullmatch(r"(.+) ([A-Z]{1,4})", a)
        if mm and mm.group(2) != ini:
            issues.append(
                f"initials {i+1}: mine={a!r} crossref given={m['author'][i].get('given')!r}"
            )
    cont = (m.get("container-title") or [""])[0]
    # pubmed
    try:
        es = get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&term="
            + urllib.parse.quote(doi + "[doi]")
        )
        ids = es["esearchresult"]["idlist"]
    except Exception as e:
        ids = [f"ERR {e}"]
    time.sleep(0.4)
    if str(r.get("pmid") or "") != (ids[0] if ids else ""):
        issues.append(f"pmid: mine={r.get('pmid')} pubmed={ids}")
    print(f"{key}: {'OK' if not issues else 'CHECK'} [{cont}; {len(fams)} authors]")
    for i in issues:
        print("    " + i)
