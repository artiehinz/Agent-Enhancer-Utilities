#!/usr/bin/env python3
"""Run the explicitly exploratory compact-profile abstention probe."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import random
import statistics
import subprocess
import sys
from typing import Any

from benchmark import (
    CONDITIONS,
    HERE,
    INTERNAL_TOKEN_ENV,
    load_plan,
    paired_distributions,
    protocol_sha256,
    run_one,
    verify_owned_automation_marker,
)


OUTPUT = HERE / ".local-results" / "exploratory-compact-0.6.8.json"
SCENARIO = "low-risk-abstention"
PAIRS = 5
SEED = 68020260728
ENDPOINT = "https://liberated.site/mcp?profile=compact"
BACKEND = "0.6.8"


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def host_version(executable: str) -> str:
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
        raise RuntimeError(f"unable to execute {executable}")
    return result.stdout.strip()


def is_valid(row: dict[str, Any]) -> bool:
    return (
        int(row["host_return_code"]) == 0
        and bool(row["final_response_present"])
        and int(row["host_event_errors"]) == 0
        and int(row["host_policy_declines"]) == 0
        and int(row["unexpected_mcp_calls"]) == 0
        and int(row["unmarked_sidecar_invocations"]) == 0
        and not bool(row["host_timed_out"])
    )


def summarize(
    rows: list[dict[str, Any]],
    marker_preflight: dict[str, int],
    plan: dict[str, Any],
) -> dict[str, Any]:
    distributions = paired_distributions(rows)
    token_values = [
        float(row["input_token_delta_percent"])
        for row in distributions
        if row["scenario"] == SCENARIO
        and row["input_token_delta_percent"] is not None
    ]
    latency_values = [
        float(row["wall_clock_delta_percent"])
        for row in distributions
        if row["scenario"] == SCENARIO
        and row["wall_clock_delta_percent"] is not None
    ]
    with_sidecar = [
        row for row in rows if row["condition"] == "with-sidecar"
    ]
    return {
        "schema_version": "1",
        "evidence_class": "exploratory-engineering-probe",
        "publication_eligible": False,
        "decision_use":
            "May inform a later preregistration; cannot confirm a product claim.",
        "scenario": SCENARIO,
        "pairs": PAIRS,
        "seed": SEED,
        "controls": plan["host"],
        "protocol_sha256": protocol_sha256(),
        "probe_sha256": hashlib.sha256(
            Path(__file__).read_bytes()
        ).hexdigest(),
        "marker_preflight": marker_preflight,
        "rows": rows,
        "paired_distributions": distributions,
        "result": {
            "complete": len(rows) == PAIRS * len(CONDITIONS),
            "all_rows_valid": all(is_valid(row) for row in rows),
            "with_sidecar_calls": sum(
                int(row["sidecar_calls"]) for row in with_sidecar
            ),
            "median_input_token_overhead_percent": (
                round(statistics.median(token_values), 3)
                if token_values
                else None
            ),
            "median_latency_overhead_percent": (
                round(statistics.median(latency_values), 3)
                if latency_values
                else None
            ),
            "reference_gate_percent": 5.0,
        },
    }


def main() -> int:
    if not os.environ.get(INTERNAL_TOKEN_ENV):
        raise RuntimeError(
            f"set {INTERNAL_TOKEN_ENV} before running the probe"
        )
    plan = load_plan()
    plan["host"]["agent_enhancer_endpoint"] = ENDPOINT
    plan["host"]["agent_enhancer_backend"] = BACKEND
    observed_version = host_version(str(plan["host"]["executable"]))
    if observed_version != plan["host"]["cli_version"]:
        raise RuntimeError(
            f"host drift: expected {plan['host']['cli_version']!r}, "
            f"found {observed_version!r}"
        )
    marker_preflight = verify_owned_automation_marker(plan)
    rows: list[dict[str, Any]] = []
    if OUTPUT.is_file():
        prior = json.loads(OUTPUT.read_text(encoding="utf-8"))
        current_probe_sha256 = hashlib.sha256(
            Path(__file__).read_bytes()
        ).hexdigest()
        if (
            prior.get("protocol_sha256") != protocol_sha256()
            or prior.get("probe_sha256") != current_probe_sha256
        ):
            raise RuntimeError(
                "the local probe report belongs to a different frozen "
                "protocol; preserve it under a different filename before "
                "starting a new probe"
            )
        rows = [
            row
            for row in prior.get("rows", [])
            if isinstance(row, dict) and is_valid(row)
        ]
    completed = {
        (str(row["condition"]), int(row["pair"])) for row in rows
    }
    randomizer = random.Random(SEED)
    schedule: list[tuple[str, int]] = []
    for pair in range(1, PAIRS + 1):
        order = list(CONDITIONS)
        randomizer.shuffle(order)
        schedule.extend((condition, pair) for condition in order)
    remaining = [
        item for item in schedule if item not in completed
    ]
    print(
        f"compact exploratory probe: {len(remaining)} run(s) remaining",
        flush=True,
    )
    for index, (condition, pair) in enumerate(remaining, start=1):
        print(
            f"[{index}/{len(remaining)}] pair {pair} {condition}",
            flush=True,
        )
        row = run_one(
            scenario=SCENARIO,
            condition=condition,
            pair=pair,
            phase="exploratory-compact-0.6.8",
            plan=plan,
        )
        rows.append(row)
        write_report(
            OUTPUT,
            summarize(rows, marker_preflight, plan),
        )
        print(
            f"  valid={is_valid(row)} "
            f"tokens={row['model_input_tokens']}/"
            f"{row['model_output_tokens']} "
            f"seconds={row['wall_clock_ms'] / 1000:.1f}",
            flush=True,
        )
        if not is_valid(row):
            raise RuntimeError(
                "exploratory row failed infrastructure validation"
            )
    report = summarize(rows, marker_preflight, plan)
    write_report(OUTPUT, report)
    print(json.dumps(report["result"], sort_keys=True))
    print(f"local report: {OUTPUT}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
