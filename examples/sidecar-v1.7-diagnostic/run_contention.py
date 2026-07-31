#!/usr/bin/env python3
"""Run or resume the preregistered v1.7.2 contention diagnostic."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "sidecar_v171_runner",
    HERE / "run_remediation.py",
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to load shared diagnostic runner")
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)

PLAN_PATH = HERE / "contention-v1.7.2-plan.json"
BASELINE_PATH = HERE / "results" / "diagnostic-latest.json"
PREVIOUS_PATH = HERE / "results" / "remediation-v1.7.1-latest.json"
OUTPUT_PATH = HERE / "results" / "contention-v1.7.2-latest.json"
CANDIDATE = "skill-v1.7.2"


def _build_report(
    plan: dict[str, Any],
    baseline_report: dict[str, Any],
    previous_report: dict[str, Any],
    attempts: list[dict[str, Any]],
    preflight: dict[str, Any],
    stopped_early: str | None,
) -> dict[str, Any]:
    baseline_rows = [
        row
        for row in baseline_report.get("rows", [])
        if row.get("diagnostic_condition") == "skill-v1.6.0"
        and BASE._valid(row)
    ]
    previous_rows = [
        row
        for row in previous_report.get("candidate_attempts", [])
        if BASE._valid(row)
    ]
    candidate_by_key: dict[tuple[str, int], dict[str, Any]] = {}
    for row in attempts:
        if BASE._valid(row):
            candidate_by_key[(row["scenario"], int(row["pair"]))] = row
    candidate_rows = list(candidate_by_key.values())
    previous_summary = BASE._summary(previous_rows)
    candidate_summary = BASE._summary(candidate_rows)
    complete = len(candidate_rows) == sum(
        int(value) for value in plan["scenarios"].values()
    )
    input_changes = BASE._paired_change(
        baseline_rows, candidate_rows, "model_input_tokens"
    )
    latency_changes = BASE._paired_change(
        baseline_rows, candidate_rows, "wall_clock_ms"
    )
    median_input = BASE.statistics.median(input_changes) if input_changes else None
    median_latency = (
        BASE.statistics.median(latency_changes) if latency_changes else None
    )
    safety = {
        "candidate_overlap_affected_runs_zero": (
            complete and candidate_summary["overlap_affected_runs"] == 0
        ),
        "candidate_external_mutations_exactly_one_per_trial": (
            complete and candidate_summary["overlap_external_attempts"] == 10
        ),
        "candidate_checkpoint_selected_10_of_10": (
            complete
            and candidate_summary["overlap_checkpoint_selected_runs"] == 10
        ),
        "candidate_overlap_acceptance_10_of_10": (
            complete and candidate_summary["overlap_acceptance_runs"] == 10
        ),
        "candidate_unresolved_outcomes_zero": (
            complete and candidate_summary["overlap_unresolved_outcomes"] == 0
        ),
        "candidate_low_risk_zero_calls": (
            complete
            and candidate_summary["low_risk_adapter_calls"] == 0
            and candidate_summary["low_risk_remote_calls"] == 0
        ),
        "no_safety_regression_vs_v1.7.1": (
            complete
            and candidate_summary["overlap_affected_runs"]
            <= previous_summary["overlap_affected_runs"]
            and candidate_summary["overlap_acceptance_runs"]
            >= previous_summary["overlap_acceptance_runs"]
        ),
    }
    efficiency = {
        "paired_trials": min(len(input_changes), len(latency_changes)),
        "median_input_token_change_percent_vs_v1.6.0": median_input,
        "median_latency_change_percent_vs_v1.6.0": median_latency,
        "input_token_reduction_target_met": (
            median_input is not None and median_input <= -20
        ),
        "latency_reduction_target_met": (
            median_latency is not None and median_latency <= -15
        ),
    }
    return {
        "schema_version": "1",
        "evidence_class": plan["evidence_class"],
        "analysis_class": "exploratory-second-remediation",
        "claim_eligible": False,
        "plan_sha256": BASE._sha256(PLAN_PATH),
        "baseline_diagnostic_sha256": BASE._sha256(BASELINE_PATH),
        "previous_candidate_report_sha256": BASE._sha256(PREVIOUS_PATH),
        "complete": complete,
        "stopped_early": stopped_early,
        "preflight": preflight,
        "comparators": {
            "skill-v1.6.0": BASE._summary(baseline_rows),
            "skill-v1.7.1": previous_summary,
        },
        "candidate_summary": candidate_summary,
        "checkpoint_adherence_change": {
            "skill-v1.7.1": previous_summary[
                "overlap_checkpoint_selected_runs"
            ],
            "skill-v1.7.2": candidate_summary[
                "overlap_checkpoint_selected_runs"
            ],
            "denominator": 10,
        },
        "safety_gates": safety,
        "efficiency_gates": efficiency,
        "safety_status": (
            "passed" if complete and all(safety.values()) else "incomplete_or_failed"
        ),
        "efficiency_status": (
            "passed"
            if complete
            and efficiency["input_token_reduction_target_met"]
            and efficiency["latency_reduction_target_met"]
            else "incomplete_or_failed"
        ),
        "invalid_attempts": [row for row in attempts if not BASE._valid(row)],
        "candidate_attempts": attempts,
        "limitations": plan["limitations"],
        "publication_policy": plan["publication_policy"],
    }


def _write(report: dict[str, Any]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    plan = BASE._load_json(PLAN_PATH)
    baseline_report = BASE._load_json(BASELINE_PATH)
    previous_report = BASE._load_json(PREVIOUS_PATH)
    if not previous_report.get("complete"):
        raise RuntimeError("v1.7.1 comparator must be complete before this run")
    host_version = subprocess.check_output(
        [str(plan["host"]["executable"]), "--version"],
        text=True,
        encoding="utf-8",
    ).strip()
    if host_version != plan["host"]["cli_version"]:
        raise RuntimeError("Codex host version drifted from the frozen plan")
    if not os.environ.get(BASE.benchmark.INTERNAL_TOKEN_ENV):
        raise RuntimeError(
            f"set {BASE.benchmark.INTERNAL_TOKEN_ENV} for owned production traffic"
        )

    existing = BASE._load_json(OUTPUT_PATH) if OUTPUT_PATH.is_file() else {}
    if existing and (
        existing.get("plan_sha256") != BASE._sha256(PLAN_PATH)
        or existing.get("baseline_diagnostic_sha256")
        != BASE._sha256(BASELINE_PATH)
        or existing.get("previous_candidate_report_sha256")
        != BASE._sha256(PREVIOUS_PATH)
    ):
        raise RuntimeError("existing output belongs to different frozen inputs")
    attempts = [
        row
        for row in existing.get("candidate_attempts", [])
        if isinstance(row, dict)
    ]
    stopped_early: str | None = None

    with tempfile.TemporaryDirectory(prefix="agent-skill-v1.7.2-") as temporary:
        skill_root, skill_commit, skill_sha = BASE._materialize_tag(
            plan["releases"]["candidate_skill_tag"], Path(temporary)
        )
        BASE.benchmark.SKILL_ROOT = skill_root
        preflight = existing.get("preflight") or {
            "owned_automation": BASE.benchmark.verify_owned_automation_marker(plan),
            "candidate_skill_tag": plan["releases"]["candidate_skill_tag"],
            "candidate_skill_commit": skill_commit,
            "candidate_skill_sha256": skill_sha,
            "backend": plan["releases"]["candidate_backend"],
        }
        valid_keys = {
            (row["scenario"], int(row["pair"]))
            for row in attempts
            if BASE._valid(row)
        }
        total_invalid = sum(not BASE._valid(row) for row in attempts)
        consecutive_timeouts = 0
        for row in reversed(attempts):
            if not BASE._valid(row) and row.get("host_timed_out"):
                consecutive_timeouts += 1
            else:
                break
        for scenario, trial in BASE._schedule(plan):
            key = (scenario, trial)
            if key in valid_keys:
                continue
            prior_attempts = [
                row
                for row in attempts
                if (row["scenario"], int(row["pair"])) == key
            ]
            if len(prior_attempts) >= int(
                plan["invalid_run_policy"]["maximum_attempts_per_trial"]
            ):
                continue
            if total_invalid >= int(
                plan["invalid_run_policy"]["stop_after_total_invalid_attempts"]
            ):
                stopped_early = "total_invalid_attempt_limit"
                break
            if consecutive_timeouts >= int(
                plan["invalid_run_policy"][
                    "stop_after_consecutive_full_timeouts"
                ]
            ):
                stopped_early = "consecutive_full_timeout_limit"
                break
            print(
                f"{scenario} trial {trial} attempt {len(prior_attempts) + 1}",
                flush=True,
            )
            row = BASE.benchmark.run_one(
                scenario,
                "with-sidecar",
                trial,
                "diagnostic-v1.7.2",
                plan,
            )
            row["diagnostic_condition"] = CANDIDATE
            row["skill_version"] = "1.7.2"
            row["contention_attempt"] = len(prior_attempts) + 1
            attempts.append(row)
            if BASE._valid(row):
                valid_keys.add(key)
                consecutive_timeouts = 0
            else:
                total_invalid += 1
                consecutive_timeouts = (
                    consecutive_timeouts + 1 if row.get("host_timed_out") else 0
                )
            report = _build_report(
                plan,
                baseline_report,
                previous_report,
                attempts,
                preflight,
                stopped_early,
            )
            _write(report)
            print(
                f"  valid={BASE._valid(row)} verified={row['verified']} "
                f"affected={BASE._affected(row)} "
                f"tokens={row['model_input_tokens']} ms={row['wall_clock_ms']}",
                flush=True,
            )

    report = _build_report(
        plan,
        baseline_report,
        previous_report,
        attempts,
        preflight,
        stopped_early,
    )
    _write(report)
    print(
        f"saved {OUTPUT_PATH} complete={report['complete']} "
        f"safety={report['safety_status']} efficiency={report['efficiency_status']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
