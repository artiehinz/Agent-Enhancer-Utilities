#!/usr/bin/env python3
"""Run or resume the exploratory v1.7 three-condition diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import random
import statistics
import subprocess
import sys
import tempfile
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE_HARNESS = ROOT / "examples" / "on-demand-agent-benchmark"
sys.path.insert(0, str(BASE_HARNESS))
benchmark = importlib.import_module("benchmark")

PLAN_PATH = HERE / "preregistered-plan.json"
OUTPUT_PATH = HERE / "results" / "diagnostic-latest.json"
CONDITIONS = ("no-sidecar", "skill-v1.6.0", "skill-v1.7.0")
SKILL_PATH = Path("skills/guard-external-plugin-workflows")


def _load_plan() -> dict[str, Any]:
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def _plan_sha256() -> str:
    return hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest()


def _host_version(executable: str) -> str:
    completed = subprocess.run(
        [executable, "--version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("unable to execute the frozen Codex host")
    return completed.stdout.strip()


def _materialize_skill(tag: str, destination: Path) -> Path:
    skill_root = destination / SKILL_PATH
    for relative in benchmark.SKILL_PROTOCOL_FILES:
        target = skill_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        content = subprocess.check_output(
            ["git", "show", f"{tag}:{(SKILL_PATH / relative).as_posix()}"],
            cwd=ROOT,
        )
        target.write_bytes(content)
    return skill_root


def _schedule(plan: dict[str, Any]) -> list[tuple[str, str, int]]:
    rng = random.Random(int(plan["seed"]))
    schedule: list[tuple[str, str, int]] = []
    for scenario, trials in plan["scenarios"].items():
        for trial in range(1, int(trials) + 1):
            order = list(CONDITIONS)
            rng.shuffle(order)
            schedule.extend((scenario, condition, trial) for condition in order)
    return schedule


def _valid(row: dict[str, Any]) -> bool:
    return (
        int(row.get("host_return_code", 1)) == 0
        and not bool(row.get("host_timed_out", False))
        and int(row.get("host_event_errors", 0)) == 0
        and int(row.get("host_policy_declines", 0)) == 0
        and int(row.get("unexpected_mcp_calls", 0)) == 0
        and int(row.get("unmarked_sidecar_invocations", 0)) == 0
        and bool(row.get("final_response_present", False))
    )


def _affected(row: dict[str, Any]) -> bool:
    return any(
        int(row.get(field, 0)) > 0
        for field in (
            "duplicate_mutations",
            "conflicting_actions",
            "provider_rejections",
            "unresolved_ambiguous",
        )
    )


def _paired_change(
    rows: list[dict[str, Any]], field: str
) -> list[float]:
    by_key = {
        (row["scenario"], int(row["pair"]), row["diagnostic_condition"]): row
        for row in rows
        if _valid(row)
    }
    changes: list[float] = []
    for trial in range(1, 11):
        current = by_key.get(("overlapping-workers", trial, "skill-v1.6.0"))
        candidate = by_key.get(("overlapping-workers", trial, "skill-v1.7.0"))
        if not current or not candidate:
            continue
        baseline = float(current.get(field, 0))
        if baseline > 0:
            changes.append((float(candidate.get(field, 0)) - baseline) / baseline * 100)
    return changes


def _build_report(
    plan: dict[str, Any], rows: list[dict[str, Any]], preflights: dict[str, Any]
) -> dict[str, Any]:
    valid_rows = [row for row in rows if _valid(row)]
    summaries: dict[str, Any] = {}
    for condition in CONDITIONS:
        selected = [
            row for row in valid_rows if row["diagnostic_condition"] == condition
        ]
        overlap = [
            row for row in selected if row["scenario"] == "overlapping-workers"
        ]
        low_risk = [
            row for row in selected if row["scenario"] == "low-risk-abstention"
        ]
        summaries[condition] = {
            "valid_runs": len(selected),
            "overlap_runs": len(overlap),
            "overlap_affected_runs": sum(_affected(row) for row in overlap),
            "overlap_acceptance_runs": sum(bool(row.get("verified")) for row in overlap),
            "overlap_external_attempts": sum(
                int(row.get("external_attempts", 0)) for row in overlap
            ),
            "overlap_unresolved_outcomes": sum(
                int(row.get("unresolved_ambiguous", 0)) for row in overlap
            ),
            "overlap_checkpoint_selected_runs": sum(
                "workflow-checkpoint" in row.get("sidecar_tools", [])
                for row in overlap
            ),
            "low_risk_runs": len(low_risk),
            "low_risk_adapter_calls": sum(
                int(row.get("adapter_calls", 0)) for row in low_risk
            ),
            "low_risk_remote_calls": sum(
                int(row.get("sidecar_calls", 0)) for row in low_risk
            ),
        }

    input_changes = _paired_change(valid_rows, "model_input_tokens")
    latency_changes = _paired_change(valid_rows, "wall_clock_ms")
    candidate = summaries["skill-v1.7.0"]
    current = summaries["skill-v1.6.0"]
    complete = len(valid_rows) == 45
    safety = {
        "candidate_overlap_affected_runs_zero": (
            complete and candidate["overlap_affected_runs"] == 0
        ),
        "candidate_external_mutations_exactly_one_per_trial": (
            complete and candidate["overlap_external_attempts"] == 10
        ),
        "candidate_checkpoint_selected_10_of_10": (
            complete and candidate["overlap_checkpoint_selected_runs"] == 10
        ),
        "candidate_overlap_acceptance_10_of_10": (
            complete and candidate["overlap_acceptance_runs"] == 10
        ),
        "candidate_unresolved_outcomes_zero": (
            complete and candidate["overlap_unresolved_outcomes"] == 0
        ),
        "candidate_low_risk_zero_calls": (
            complete
            and candidate["low_risk_adapter_calls"] == 0
            and candidate["low_risk_remote_calls"] == 0
        ),
        "no_safety_regression_vs_v1.6.0": (
            complete
            and candidate["overlap_affected_runs"]
            <= current["overlap_affected_runs"]
            and candidate["overlap_acceptance_runs"]
            >= current["overlap_acceptance_runs"]
        ),
    }
    median_input = statistics.median(input_changes) if input_changes else None
    median_latency = statistics.median(latency_changes) if latency_changes else None
    efficiency = {
        "paired_trials": min(len(input_changes), len(latency_changes)),
        "median_input_token_change_percent": median_input,
        "median_latency_change_percent": median_latency,
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
        "analysis_class": "exploratory",
        "claim_eligible": False,
        "plan_sha256": _plan_sha256(),
        "complete": complete,
        "execution_constraint": plan["execution_constraint"],
        "preflights": preflights,
        "summaries": summaries,
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
        "invalid_runs": [row for row in rows if not _valid(row)],
        "rows": rows,
        "limitations": [
            plan["execution_constraint"],
            "The destination and injected failure are synthetic.",
            "One model and one reasoning setting do not establish universal agent behavior.",
            "ChatGPT-managed authentication exposes tokens but no defensible per-run dollar cost.",
            "Neutral and negative efficiency results remain in the report.",
        ],
    }


def _write(report: dict[str, Any]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(report, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--condition", choices=CONDITIONS, required=True)
    args = parser.parse_args()
    plan = _load_plan()
    if _host_version(plan["host"]["executable"]) != plan["host"]["cli_version"]:
        raise RuntimeError("Codex host version drifted from the frozen plan")
    if args.condition != "no-sidecar" and not os.environ.get(
        benchmark.INTERNAL_TOKEN_ENV
    ):
        raise RuntimeError(
            f"set {benchmark.INTERNAL_TOKEN_ENV} for owned production traffic"
        )

    existing: dict[str, Any] = {}
    if OUTPUT_PATH.is_file():
        existing = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        if existing.get("plan_sha256") != _plan_sha256():
            raise RuntimeError("existing output belongs to a different plan")
    rows = [row for row in existing.get("rows", []) if isinstance(row, dict)]
    preflights = dict(existing.get("preflights", {}))

    with tempfile.TemporaryDirectory(prefix="agent-skill-versions-") as temporary:
        temporary_root = Path(temporary)
        if args.condition == "skill-v1.6.0":
            benchmark.SKILL_ROOT = _materialize_skill("v1.6.0", temporary_root)
        elif args.condition == "skill-v1.7.0":
            benchmark.SKILL_ROOT = ROOT / SKILL_PATH

        if args.condition != "no-sidecar" and args.condition not in preflights:
            preflights[args.condition] = {
                "owned_automation": benchmark.verify_owned_automation_marker(plan),
                "skill_protocol_sha256": benchmark.protocol_sha256(),
                "backend": plan["releases"][
                    "current_backend"
                    if args.condition == "skill-v1.6.0"
                    else "candidate_backend"
                ],
            }

        done = {
            (row["scenario"], row["diagnostic_condition"], int(row["pair"]))
            for row in rows
            if _valid(row)
        }
        selected = [
            item
            for item in _schedule(plan)
            if item[1] == args.condition
            and (item[0], item[1], item[2]) not in done
        ]
        for index, (scenario, condition, trial) in enumerate(selected, start=1):
            print(
                f"[{index}/{len(selected)}] {scenario} trial {trial} {condition}",
                flush=True,
            )
            internal_condition = (
                "without-sidecar" if condition == "no-sidecar" else "with-sidecar"
            )
            row = benchmark.run_one(
                scenario,
                internal_condition,
                trial,
                "diagnostic-v1.7",
                plan,
            )
            row["diagnostic_condition"] = condition
            row["skill_version"] = None if condition == "no-sidecar" else condition[6:]
            rows = [
                prior
                for prior in rows
                if not (
                    prior.get("scenario") == scenario
                    and prior.get("diagnostic_condition") == condition
                    and int(prior.get("pair", 0)) == trial
                )
            ]
            rows.append(row)
            rows.sort(
                key=lambda item: (
                    item["scenario"],
                    int(item["pair"]),
                    CONDITIONS.index(item["diagnostic_condition"]),
                )
            )
            _write(_build_report(plan, rows, preflights))
            print(
                f"  verified={row['verified']} affected={_affected(row)} "
                f"tokens={row['model_input_tokens']} ms={row['wall_clock_ms']}",
                flush=True,
            )

    report = _build_report(plan, rows, preflights)
    _write(report)
    print(
        f"saved {OUTPUT_PATH} complete={report['complete']} "
        f"safety={report['safety_status']} efficiency={report['efficiency_status']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
