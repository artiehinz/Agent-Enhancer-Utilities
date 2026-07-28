#!/usr/bin/env python3
"""Run the pre-registered paired reliability benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from benchmark import build_report, compact_report, load_plan


HERE = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--plan",
        type=Path,
        default=HERE / "preregistered-plan.json",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = compact_report(build_report(load_plan(args.plan)))
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
