#!/usr/bin/env python3
"""Run or resume the preregistered metered Codex benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from benchmark import (
    HERE,
    INTERNAL_TOKEN_ENV,
    SCENARIOS,
    build_report,
    load_plan,
    protocol_sha256,
    randomized_schedule,
    run_one,
)


DEFAULT_LOCAL_OUTPUT = HERE / ".local-results" / "validation.json"
DEFAULT_PUBLIC_OUTPUT = HERE / "results" / "latest.json"


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def _load_report(
    path: Path,
    phase: str,
    expected_plan_sha256: str,
    expected_protocol_sha256: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not path.is_file():
        return [], []
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("phase") != phase:
        raise RuntimeError(
            f"{path} contains phase {report.get('phase')!r}, not {phase!r}"
        )
    if (
        report.get("plan_sha256") != expected_plan_sha256
        or report.get("protocol_sha256") != expected_protocol_sha256
    ):
        if phase == "publication":
            raise RuntimeError(
                f"{path} belongs to a different preregistration; preserve it "
                "and select a new output path"
            )
        prior = [
            row
            for row in [
                *report.get("rows", []),
                *report.get("infrastructure_exclusions", []),
            ]
            if isinstance(row, dict)
        ]
        for row in prior:
            row["exclusion_reason"] = "plan_changed_before_valid_run"
        return [], prior
    rows = report.get("rows", [])
    if not isinstance(rows, list):
        raise RuntimeError(f"{path} does not contain a rows list")
    exclusions = report.get("infrastructure_exclusions", [])
    if not isinstance(exclusions, list):
        exclusions = []
    valid_rows = [
        row
        for row in rows
        if isinstance(row, dict)
        and int(row.get("host_return_code", 1)) == 0
        and bool(row.get("final_response_present", False))
        and int(row.get("host_event_errors", 0)) == 0
        and int(row.get("host_policy_declines", 0)) == 0
        and int(row.get("unexpected_mcp_calls", 0)) == 0
        and not bool(row.get("host_timed_out", False))
    ]
    invalid_rows = [
        row
        for row in rows
        if isinstance(row, dict) and row not in valid_rows
    ]
    return valid_rows, [
        row
        for row in [*exclusions, *invalid_rows]
        if isinstance(row, dict)
    ]


def _host_version(executable: str) -> str:
    result = subprocess.run(
        [executable, "--version"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"unable to execute {executable}: {result.stderr}")
    return result.stdout.strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase",
        choices=("validation", "publication"),
        default="validation",
    )
    parser.add_argument("--pairs", type=int)
    parser.add_argument(
        "--scenario",
        action="append",
        choices=SCENARIOS,
        dest="scenarios",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--keep-workspaces",
        action="store_true",
        help="Keep local prompts, stderr, and event logs for debugging.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = load_plan()
    expected_pairs = int(
        plan[
            "validation_pairs_per_scenario"
            if args.phase == "validation"
            else "published_pairs_per_scenario"
        ]
    )
    pairs = args.pairs if args.pairs is not None else expected_pairs
    if pairs < 1 or pairs > expected_pairs:
        raise RuntimeError(f"--pairs must be between 1 and {expected_pairs}")
    scenarios = tuple(args.scenarios or SCENARIOS)
    output = args.output or (
        DEFAULT_LOCAL_OUTPUT
        if args.phase == "validation"
        else DEFAULT_PUBLIC_OUTPUT
    )

    version = _host_version(str(plan["host"]["executable"]))
    if version != plan["host"]["cli_version"]:
        raise RuntimeError(
            f"host drift: expected {plan['host']['cli_version']!r}, "
            f"found {version!r}; amend and re-register before running"
        )
    if not os.environ.get(INTERNAL_TOKEN_ENV):
        raise RuntimeError(
            f"set {INTERNAL_TOKEN_ENV} so owned production MCP calls are "
            "excluded from public usage"
        )

    plan_sha256 = hashlib.sha256(
        (HERE / "preregistered-plan.json").read_bytes()
    ).hexdigest()
    rows, infrastructure_exclusions = _load_report(
        output,
        args.phase,
        plan_sha256,
        protocol_sha256(),
    )
    failed_pairs = {
        (str(row.get("scenario")), int(row.get("pair", 0)))
        for row in infrastructure_exclusions
    }
    complete_pairs = {
        (str(row.get("scenario")), int(row.get("pair", 0)))
        for row in rows
        if {
            str(candidate.get("condition"))
            for candidate in rows
            if candidate.get("scenario") == row.get("scenario")
            and int(candidate.get("pair", 0)) == int(row.get("pair", 0))
        }
        == {"without-sidecar", "with-sidecar"}
    }
    unresolved_failed_pairs = failed_pairs - complete_pairs
    if unresolved_failed_pairs:
        retained_rows = [
            row
            for row in rows
            if (str(row.get("scenario")), int(row.get("pair", 0)))
            not in unresolved_failed_pairs
        ]
        infrastructure_exclusions.extend(
            row for row in rows if row not in retained_rows
        )
        rows = retained_rows
    completed = {
        (
            str(row.get("scenario")),
            str(row.get("condition")),
            int(row.get("pair", 0)),
        )
        for row in rows
    }
    keep_root = (
        HERE / ".local-results" / "workspaces"
        if args.keep_workspaces
        else None
    )
    schedule = randomized_schedule(plan, args.phase, pairs, scenarios)
    remaining = [
        item
        for item in schedule
        if (item[0], item[1], item[2]) not in completed
    ]
    print(
        f"{args.phase}: {len(remaining)} run(s) remaining; "
        f"{len(rows)} row(s) already recorded",
        flush=True,
    )
    for index, (scenario, condition, pair) in enumerate(remaining, start=1):
        print(
            f"[{index}/{len(remaining)}] {scenario} pair {pair} {condition}",
            flush=True,
        )
        row = run_one(
            scenario=scenario,
            condition=condition,
            pair=pair,
            phase=args.phase,
            plan=plan,
            keep_workspace=keep_root,
        )
        if (
            int(row["host_return_code"]) != 0
            or not bool(row["final_response_present"])
            or int(row["host_event_errors"]) != 0
            or int(row["host_policy_declines"]) != 0
            or int(row["unexpected_mcp_calls"]) != 0
            or bool(row["host_timed_out"])
        ):
            infrastructure_exclusions.append(row)
            rows = [
                candidate
                for candidate in rows
                if not (
                    candidate["scenario"] == scenario
                    and int(candidate["pair"]) == pair
                )
            ]
        else:
            rows.append(row)
        report = build_report(plan, args.phase, rows)
        report["infrastructure_exclusions"] = infrastructure_exclusions
        _write_report(output, report)
        print(
            "  verified="
            f"{row['verified']} harm="
            f"{row['duplicate_mutations'] + row['conflicting_actions'] + row['provider_rejections'] + row['unresolved_ambiguous']} "
            f"sidecar_calls={row['sidecar_calls']} "
            f"tokens={row['model_input_tokens']}/{row['model_output_tokens']} "
            f"seconds={row['wall_clock_ms'] / 1000:.1f}",
            flush=True,
        )
    print(f"report: {output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
