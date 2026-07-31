#!/usr/bin/env python3
"""Recompute descriptive run-level evidence from a frozen benchmark report."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
RISK_SCENARIOS = (
    "ambiguous-success-create",
    "overlapping-workers",
    "shared-rate-limit",
    "scheduled-refresh",
)
CONDITIONS = ("without-sidecar", "with-sidecar")
CONFIRMED_HARM_FIELDS = (
    "duplicate_mutations",
    "conflicting_actions",
    "provider_rejections",
)


def _percentile(values: Iterable[float], percentile: float) -> float | None:
    """Return an R-7/NumPy-style linearly interpolated percentile."""
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    rank = (len(ordered) - 1) * percentile
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (
        rank - lower
    )


def _rounded_percentile(
    values: Iterable[float], percentile: float, *, digits: int
) -> float | int | None:
    value = _percentile(values, percentile)
    if value is None:
        return None
    rounded = round(value, digits)
    return int(rounded) if digits == 0 else rounded


def _distribution(values: Iterable[float], *, digits: int) -> dict[str, Any]:
    materialized = list(values)
    return {
        "method": "linear_interpolation_r7",
        "p50": _rounded_percentile(materialized, 0.50, digits=digits),
        "p90": _rounded_percentile(materialized, 0.90, digits=digits),
        "p95": _rounded_percentile(materialized, 0.95, digits=digits),
    }


def _confirmed_harm(row: dict[str, Any]) -> int:
    return sum(int(row.get(field, 0)) for field in CONFIRMED_HARM_FIELDS)


def _condition_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    categories = {
        field: sum(int(row.get(field, 0)) for row in rows)
        for field in CONFIRMED_HARM_FIELDS
    }
    accepted = sum(int(bool(row.get("verified"))) for row in rows)
    affected = sum(int(_confirmed_harm(row) > 0) for row in rows)
    unresolved_runs = sum(
        int(int(row.get("unresolved_ambiguous", 0)) > 0) for row in rows
    )
    multi_category_runs = sum(
        int(
            sum(int(int(row.get(field, 0)) > 0) for field in CONFIRMED_HARM_FIELDS)
            > 1
        )
        for row in rows
    )
    return {
        "runs": len(rows),
        "evaluator_invoked_rows": len(rows),
        "final_response_runs": sum(
            int(bool(row.get("final_response_present"))) for row in rows
        ),
        "acceptance_passed_runs": accepted,
        "acceptance_rate_percent": (
            round(accepted / len(rows) * 100, 3) if rows else None
        ),
        "runs_with_confirmed_harm": affected,
        "confirmed_harm_run_rate_percent": (
            round(affected / len(rows) * 100, 3) if rows else None
        ),
        "confirmed_harm_counters": {
            **categories,
            "pooled_total": sum(categories.values()),
        },
        "runs_with_multiple_harm_categories": multi_category_runs,
        "runs_with_unresolved_outcome": unresolved_runs,
        "unresolved_outcomes": sum(
            int(row.get("unresolved_ambiguous", 0)) for row in rows
        ),
        "manual_intervention_runs": sum(
            int(int(row.get("manual_interventions", 0)) > 0) for row in rows
        ),
        "model_input_tokens": _distribution(
            (int(row.get("model_input_tokens", 0)) for row in rows),
            digits=0,
        ),
        "wall_clock_ms": _distribution(
            (float(row.get("wall_clock_ms", 0)) for row in rows),
            digits=0,
        ),
    }


def _percentage_reduction(before: int, after: int) -> float | None:
    return round((before - after) / before * 100, 3) if before else None


def build_reanalysis(source: dict[str, Any], source_sha256: str) -> dict[str, Any]:
    rows = source.get("rows")
    paired = source.get("paired_distributions")
    if not isinstance(rows, list) or not isinstance(paired, list):
        raise ValueError("source report must include rows and paired_distributions")
    if len(rows) != 200:
        raise ValueError(f"expected 200 frozen rows, received {len(rows)}")

    scenario_summaries = []
    for scenario in (*RISK_SCENARIOS, "low-risk-abstention"):
        conditions = {
            condition: _condition_summary(
                [
                    row
                    for row in rows
                    if row.get("scenario") == scenario
                    and row.get("condition") == condition
                ]
            )
            for condition in CONDITIONS
        }
        pair_rows = [row for row in paired if row.get("scenario") == scenario]
        scenario_summaries.append(
            {
                "scenario": scenario,
                "conditions": conditions,
                "paired_delta_percentiles": {
                    "model_input_tokens": _distribution(
                        (
                            float(row["input_token_delta_percent"])
                            for row in pair_rows
                            if row.get("input_token_delta_percent") is not None
                        ),
                        digits=3,
                    ),
                    "wall_clock": _distribution(
                        (
                            float(row["wall_clock_delta_percent"])
                            for row in pair_rows
                            if row.get("wall_clock_delta_percent") is not None
                        ),
                        digits=3,
                    ),
                },
            }
        )

    risk = {}
    for condition in CONDITIONS:
        risk[condition] = _condition_summary(
            [
                row
                for row in rows
                if row.get("scenario") in RISK_SCENARIOS
                and row.get("condition") == condition
            ]
        )
    without = risk["without-sidecar"]
    guarded = risk["with-sidecar"]

    return {
        "schema_version": "1",
        "analysis_class": "post-hoc-descriptive-reanalysis",
        "preregistered": False,
        "source_report": "publication-latest.json",
        "source_report_schema_version": source.get("schema_version"),
        "source_report_sha256": source_sha256,
        "source_rows_unchanged": True,
        "risk_summary": {
            "without_sidecar": without,
            "with_sidecar": guarded,
            "affected_run_reduction_percent": _percentage_reduction(
                int(without["runs_with_confirmed_harm"]),
                int(guarded["runs_with_confirmed_harm"]),
            ),
            "pooled_counter_reduction_percent": _percentage_reduction(
                int(without["confirmed_harm_counters"]["pooled_total"]),
                int(guarded["confirmed_harm_counters"]["pooled_total"]),
            ),
        },
        "scenarios": scenario_summaries,
        "interpretation": [
            "The original pooled 26-to-2 result contains confirmed duplicate, conflict, and rejection counters; unresolved outcomes were 0 in both conditions.",
            "Pooled counters are correlated: one affected run may contribute to more than one category, so affected-run counts are the primary descriptive result.",
            "The runner invoked the condition-blind evaluator for every retained run. The legacy verified field is an acceptance result, not a measure of how often the evaluator looked.",
            "This post-hoc reanalysis adds descriptive resolution only. It does not change the frozen rows, preregistered gates, or causal scope of the benchmark.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=HERE / "results" / "publication-latest.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=HERE / "results" / "publication-reanalysis.json",
    )
    args = parser.parse_args()
    source_bytes = args.input.read_bytes()
    source = json.loads(source_bytes)
    reanalysis = build_reanalysis(
        source,
        hashlib.sha256(source_bytes).hexdigest(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(reanalysis, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output)


if __name__ == "__main__":
    main()
