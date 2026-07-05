# PRISMA-Pilot

**A systematic-review screening assistant that automates the mechanical, error-prone parts of the review pipeline — deduplication, keyword screening, and PRISMA 2020 flow counts — while keeping every decision auditable.**

Systematic reviews lose enormous time to work that is tedious but not hard: reconciling duplicate hits across PubMed, Embase, and Scopus; applying the same inclusion criteria to hundreds of abstracts; and hand-counting records for the PRISMA flow diagram (where arithmetic slips are common enough that journals catch them in peer review). PRISMA-Pilot does that mechanical layer deterministically and shows its work, so a human reviewer spends their attention on the genuinely ambiguous studies instead of the obvious ones.

Zero dependencies. Pure Python standard library. Reproducible by design.

## What it does

1. **Loads** database exports in JSON, CSV, or RIS (the format PubMed, Embase, Zotero, and EndNote all export).
2. **Deduplicates** across sources using a three-tier strategy — exact DOI, exact normalized title, then year-guarded fuzzy title matching — and records *why* each duplicate was removed.
3. **Screens** titles and abstracts against a small, declarative rule set (required concepts, topic terms, exclusion terms), tagging every record with the exact terms that fired.
4. **Counts** everything into a PRISMA 2020 flow summary, with a built-in consistency check that flags arithmetic that doesn't reconcile.

## Why the "transparent" part matters

Automated abstract screeners are increasingly common, but a black-box classifier that says "exclude" without a reason is hard to defend in a methods section and impossible to reproduce. Every PRISMA-Pilot decision carries its justification:

```
[R004] exclude — exclusion term(s): murine, mice
[R001] include — matched: colorectal, outreach, screening
```

The rule set is plain JSON you can version alongside your protocol. This is a **reviewer accelerator, not a reviewer replacement** — it is designed to make the obvious excludes fast and the reasoning explicit, then hand the borderline cases to a human.

## Quick start

```bash
git clone https://github.com/YOUR-USERNAME/prisma-pilot.git
cd prisma-pilot
pip install -e .

prisma-pilot run examples/sample_records.json \
    --config examples/config.json \
    --show-included
```

Output:

```
PRISMA flow summary
===================
Records identified (all sources) ........ 12
Duplicates removed ...................... 1
Records screened (title/abstract) ....... 11
Records excluded ........................ 5
Studies included ........................ 6

Exclusion reasons:
     3  exclusion term(s)
     1  missing required concept
     1  no required topic term present
```

Export per-record decisions and the flow counts:

```bash
prisma-pilot run records.ris --config config.json \
    --out-decisions decisions.csv \
    --out-flow prisma_flow.json
```

## Screening config

A config is a small declarative spec. `include_all` requires each concept group (an OR-set) to appear — so you can require concept A **and** concept B while allowing synonyms within each. `exclude_any` drops a record on any hit.

```json
{
  "include_all": [
    ["colorectal", "colon cancer", "colorectal cancer"],
    ["outreach", "education", "navigation", "peer", "brochure", "print"]
  ],
  "include_any": ["screening"],
  "exclude_any": ["murine", "mice", "editorial"]
}
```

The example config models a real review question: comparing **peer-led verbal outreach** against **institutional print outreach** for colorectal cancer screening in underserved populations.

## Architecture

```
src/prismapilot/
├── records.py     # Record model + JSON / CSV / RIS loaders
├── dedup.py       # Three-tier deduplication (DOI -> title -> year-guarded fuzzy)
├── screen.py      # Declarative keyword screening with word-boundary matching
├── flow.py        # PRISMA 2020 flow counts + internal consistency check
├── pipeline.py    # Orchestration + CSV/JSON export
└── cli.py         # argparse CLI (dedup / run)
```

Design choices worth noting:

- **Word-boundary matching**, so `print` doesn't match inside `footprint` — a real source of false positives in naive keyword screeners. Covered by a regression test.
- **Year-guarded fuzzy dedup**: two similarly titled papers from different years are *not* merged, preventing the classic over-collapse failure.
- **Auditable removal log**: every duplicate records the id it was merged into and the reason, so the "duplicates removed" number in your PRISMA diagram is defensible.
- **Consistency check**: `flow.render()` warns if `included != screened - excluded`, catching pipeline bugs before they reach a manuscript.
- **RIS support** because that is what real bibliographic managers export — not just tidy CSVs.

## Tests

19 tests covering all three loaders, each dedup tier, the year guard, word-boundary screening, export round-trips, and flow-count integrity:

```bash
python -m pytest
```

## Scope and disclaimer

PRISMA-Pilot supports human reviewers; it does not replace dual independent screening, which remains the methodological standard. Keyword screening is deliberately conservative and transparent rather than "smart" — it is meant to triage, with a human making final inclusion decisions. Always report your automation methods in your review.

## Roadmap

- Full-text screening stage with reason codes
- Cohen's kappa between the tool and a human screener
- Direct PubMed E-utilities / Europe PMC ingestion
- PRISMA flow diagram figure export (SVG)

## License

MIT
