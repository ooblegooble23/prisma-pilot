"""prisma-pilot command-line interface.

Typical run:
    prisma-pilot run examples/sample_records.json \\
        --config examples/config.json \\
        --out-decisions decisions.csv \\
        --out-flow flow.json

Sub-commands:
    dedup   just deduplicate and report
    run     full load -> dedup -> screen -> PRISMA pipeline
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from prismapilot import __version__
from prismapilot.dedup import Deduplicator
from prismapilot.pipeline import export_decisions_csv, export_flow_json, run_pipeline
from prismapilot.records import load_records
from prismapilot.screen import ScreenConfig


def cmd_dedup(args: argparse.Namespace) -> int:
    records = load_records(args.input)
    result = Deduplicator(title_threshold=args.threshold).deduplicate(records)
    print(f"Loaded {result.n_in} records.")
    print(f"Unique:  {result.n_unique}")
    print(f"Removed: {result.n_removed}")
    if args.verbose:
        for r in result.removed:
            print(f"  - {r.record.id} duplicate of {r.duplicate_of} ({r.reason})")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    records = load_records(args.input)
    if args.config:
        config = ScreenConfig.from_dict(json.loads(Path(args.config).read_text()))
    else:
        config = ScreenConfig()
        print("No --config given; running dedup + PRISMA count with no screening rules.\n")

    output = run_pipeline(records, config, title_threshold=args.threshold)
    print(output.flow.render())

    if args.out_decisions:
        export_decisions_csv(output.decisions, args.out_decisions)
        print(f"\nPer-record decisions written to {args.out_decisions}")
    if args.out_flow:
        export_flow_json(output.flow, args.out_flow)
        print(f"PRISMA flow JSON written to {args.out_flow}")

    if args.show_included:
        print("\nIncluded studies:")
        for d in output.decisions:
            if d.decision == "include":
                yr = f" ({d.record.year})" if d.record.year else ""
                print(f"  [{d.record.id}] {d.record.title}{yr}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prisma-pilot",
        description="Systematic-review screening assistant: dedup, keyword screen, PRISMA counts.",
    )
    parser.add_argument("--version", action="version", version=f"prisma-pilot {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_dedup = sub.add_parser("dedup", help="Deduplicate records and report")
    p_dedup.add_argument("input", help="Path to .json/.csv/.ris export")
    p_dedup.add_argument("--threshold", type=float, default=0.92,
                         help="Fuzzy title similarity threshold (default 0.92)")
    p_dedup.add_argument("--verbose", action="store_true")
    p_dedup.set_defaults(func=cmd_dedup)

    p_run = sub.add_parser("run", help="Full pipeline with PRISMA output")
    p_run.add_argument("input", help="Path to .json/.csv/.ris export")
    p_run.add_argument("--config", help="Path to screening config JSON")
    p_run.add_argument("--threshold", type=float, default=0.92)
    p_run.add_argument("--out-decisions", help="Write per-record decisions to CSV")
    p_run.add_argument("--out-flow", help="Write PRISMA flow counts to JSON")
    p_run.add_argument("--show-included", action="store_true",
                       help="Print the titles of included studies")
    p_run.set_defaults(func=cmd_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
