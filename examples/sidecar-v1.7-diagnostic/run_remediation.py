#!/usr/bin/env python3
"""Run or resume the separately preregistered v1.7.1 remediation diagnostic."""

from __future__ import annotations

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

PLAN_PATH = HERE / "remediation-v1.7.1-plan.json"
SOURCE_PATH = HERE / "results" / "diagnostic-latest.json"
OUTPUT_PATH = HERE / "results" / "remediation-v1.7.1-latest.json"
SKILL_PATH = Path("skills/guard-external-plugin-workflows")
CANDIDATE = "skill-v1.7.1"


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path.name} must contain one JSON object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _materialize_tag(tag: str, destination: Path) -> tuple[Path, str, str]:
    commit = subprocess.check_output(
        ["git", "rev-parse", f"{tag}^{{commit}}"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    ).strip()
    prefix = SKILL_PATH.as_posix() + "/"
    names = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", tag, "--", prefix],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    ).splitlines()
    selected = [name for name in names if name.startswith(prefix)]
    if not selected:
        raise RuntimeError(f"{tag} does not contain the candidate skill")
    skill_root = destination / SKILL_PATH
    digest = hashlib.sha256()
    for name in sorted(selected):
        relative = Path(name).relative_to(SKILL_PATH)
        if "__pycache__" in relative.parts or relative.suffix == ".pyc":
            continue
        content = subprocess.check_output(["git", "show", f"{tag}:{name}"], cwd=ROOT)
        target = skill_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(content.replace(b"\r\n", b"\n").replace(b"\r", b"\n"))
        digest.update(b"\0")
    return skill_root, commit, digest.hexdigest()


def _schedule(plan: dict[str, Any]) -> list[tuple[str, int]]:
    values = [
        (scenario, trial)
        for scenario, count in plan["scenarios"].items()
        for trial in range(1, int(count) + 1)
    ]
    random.Random(int(plan["seed"])).shuffle(values)
    return values


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    selected = [row for row in rows if _valid(row)]
    overlap = [row for row in selected if row["scenario"] == "overlapping-workers"]
    low_risk = [row for row in selected if row["scenario"] == "low-risk-abstention"]
    return {
        "valid_runs": len(selected),
        "overlap_runs": len(overlap),
        "overlap_affected_runs": sum(_affected(row) for row in overlap),
        "overlap_acceptance_runs": sum(bool(row.get("verified")) for row in overlap),
        "overlap_external_attempts": sum(int(row.get("external_attempts", 0)) for row in overlap),
        "overlap_unresolved_outcomes": sum(int(row.get("unresolved_ambiguous", 0)) for row in overlap),
        "overlap_checkpoint_selected_runs": sum(
            "workflow-checkpoint" in row.get("sidecar_tools", []) for row in overlap
        ),
        "low_risk_runs": len(low_risk),
        "low_risk_adapter_calls": sum(int(row.get("adapter_calls", 0)) for row in low_risk),
        "low_risk_remote_calls": sum(int(row.get("sidecar_calls", 0)) for row in low_risk),
    }


def _paired_change(
    baseline: list[dict[str, Any]], candidate: list[dict[str, Any]], field: str
) -> list[float]:
    before = {
        int(row["pair"]): row
        for row in baseline
        if _valid(row) and row["scenario"] == "overlapping-workers"
    }
    after = {
        int(row["pair"]): row
        for row in candidate
        if _valid(row) and row["scenario"] == "overlapping-workers"
    }
    changes: list[float] = []
    for trial in sorted(set(before) & set(after)):
        denominator = float(before[trial].get(field, 0))
        if denominator > 0:
            changes.append((float(after[trial].get(field, 0)) - denominator) / denominator * 100)
    return changes


def _build_report(
    plan: dict[str, Any],
    source: dict[str, Any],
    attempts: list[dict[str, Any]],
    preflight: dict[str, Any],
    stopped_early: str | None,
) -> dict[str, Any]:
    baseline_rows = [
        row
        for row in source.get("rows", [])
        if row.get("diagnostic_condition") == "skill-v1.6.0" and _valid(row)
    ]
    candidate_by_key: dict[tuple[str, int], dict[str, Any]] = {}
    for row in attempts:
        if _valid(row):
            candidate_by_key[(row["scenario"], int(row["pair"]))] = row
    candidate_rows = list(candidate_by_key.values())
    baseline_summary = _summary(baseline_rows)
    candidate_summary = _summary(candidate_rows)
    complete = len(candidate_rows) == sum(int(value) for value in plan["scenarios"].values())
    input_changes = _paired_change(baseline_rows, candidate_rows, "model_input_tokens")
    latency_changes = _paired_change(baseline_rows, candidate_rows, "wall_clock_ms")
    median_input = statistics.median(input_changes) if input_changes else None
    median_latency = statistics.median(latency_changes) if latency_changes else None
    safety = {
        "candidate_overlap_affected_runs_zero": complete and candidate_summary["overlap_affected_runs"] == 0,
        "candidate_external_mutations_exactly_one_per_trial": complete and candidate_summary["overlap_external_attempts"] == 10,
        "candidate_checkpoint_selected_10_of_10": complete and candidate_summary["overlap_checkpoint_selected_runs"] == 10,
        "candidate_overlap_acceptance_10_of_10": complete and candidate_summary["overlap_acceptance_runs"] == 10,
        "candidate_unresolved_outcomes_zero": complete and candidate_summary["overlap_unresolved_outcomes"] == 0,
        "candidate_low_risk_zero_calls": complete and candidate_summary["low_risk_adapter_calls"] == 0 and candidate_summary["low_risk_remote_calls"] == 0,
        "no_safety_regression_vs_v1.6.0": complete and candidate_summary["overlap_affected_runs"] <= baseline_summary["overlap_affected_runs"] and candidate_summary["overlap_acceptance_runs"] >= baseline_summary["overlap_acceptance_runs"],
    }
    efficiency = {
        "paired_trials": min(len(input_changes), len(latency_changes)),
        "median_input_token_change_percent": median_input,
        "median_latency_change_percent": median_latency,
        "input_token_reduction_target_met": median_input is not None and median_input <= -20,
        "latency_reduction_target_met": median_latency is not None and median_latency <= -15,
    }
    return {
        "schema_version": "1",
        "evidence_class": plan["evidence_class"],
        "analysis_class": "exploratory-post-failure-remediation",
        "claim_eligible": False,
        "plan_sha256": _sha256(PLAN_PATH),
        "source_diagnostic_sha256": _sha256(SOURCE_PATH),
        "complete": complete,
        "stopped_early": stopped_early,
        "preflight": preflight,
        "source_summaries": {
            "no-sidecar": source.get("summaries", {}).get("no-sidecar"),
            "skill-v1.6.0": source.get("summaries", {}).get("skill-v1.6.0"),
            "skill-v1.7.0": source.get("summaries", {}).get("skill-v1.7.0"),
            "skill-v1.7.0_invalid_runs": len(source.get("invalid_runs", [])),
        },
        "candidate_summary": candidate_summary,
        "safety_gates": safety,
        "efficiency_gates": efficiency,
        "safety_status": "passed" if complete and all(safety.values()) else "incomplete_or_failed",
        "efficiency_status": "passed" if complete and efficiency["input_token_reduction_target_met"] and efficiency["latency_reduction_target_met"] else "incomplete_or_failed",
        "invalid_attempts": [row for row in attempts if not _valid(row)],
        "candidate_attempts": attempts,
        "limitations": plan["limitations"],
        "publication_policy": plan["publication_policy"],
    }


def _write(report: dict[str, Any]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    plan = _load_json(PLAN_PATH)
    source = _load_json(SOURCE_PATH)
    if source.get("plan_sha256") != _sha256(HERE / "preregistered-plan.json"):
        raise RuntimeError("source diagnostic no longer matches its frozen plan")
    host_version = subprocess.check_output(
        [str(plan["host"]["executable"]), "--version"],
        text=True,
        encoding="utf-8",
    ).strip()
    if host_version != plan["host"]["cli_version"]:
        raise RuntimeError("Codex host version drifted from the frozen plan")
    if not os.environ.get(benchmark.INTERNAL_TOKEN_ENV):
        raise RuntimeError(f"set {benchmark.INTERNAL_TOKEN_ENV} for owned production traffic")

    existing = _load_json(OUTPUT_PATH) if OUTPUT_PATH.is_file() else {}
    if existing and (
        existing.get("plan_sha256") != _sha256(PLAN_PATH)
        or existing.get("source_diagnostic_sha256") != _sha256(SOURCE_PATH)
    ):
        raise RuntimeError("existing remediation output belongs to different frozen inputs")
    attempts = [row for row in existing.get("candidate_attempts", []) if isinstance(row, dict)]
    stopped_early: str | None = None

    with tempfile.TemporaryDirectory(prefix="agent-skill-v1.7.1-") as temporary:
        skill_root, skill_commit, skill_sha = _materialize_tag(
            plan["releases"]["candidate_skill_tag"], Path(temporary)
        )
        benchmark.SKILL_ROOT = skill_root
        preflight = existing.get("preflight") or {
            "owned_automation": benchmark.verify_owned_automation_marker(plan),
            "candidate_skill_tag": plan["releases"]["candidate_skill_tag"],
            "candidate_skill_commit": skill_commit,
            "candidate_skill_sha256": skill_sha,
            "backend": plan["releases"]["candidate_backend"],
        }
        valid_keys = {
            (row["scenario"], int(row["pair"])) for row in attempts if _valid(row)
        }
        total_invalid = sum(not _valid(row) for row in attempts)
        consecutive_timeouts = 0
        for row in reversed(attempts):
            if not _valid(row) and row.get("host_timed_out"):
                consecutive_timeouts += 1
            else:
                break
        for scenario, trial in _schedule(plan):
            key = (scenario, trial)
            if key in valid_keys:
                continue
            prior_attempts = [
                row for row in attempts if (row["scenario"], int(row["pair"])) == key
            ]
            if len(prior_attempts) >= int(plan["invalid_run_policy"]["maximum_attempts_per_trial"]):
                continue
            if total_invalid >= int(plan["invalid_run_policy"]["stop_after_total_invalid_attempts"]):
                stopped_early = "total_invalid_attempt_limit"
                break
            if consecutive_timeouts >= int(plan["invalid_run_policy"]["stop_after_consecutive_full_timeouts"]):
                stopped_early = "consecutive_full_timeout_limit"
                break
            print(f"{scenario} trial {trial} attempt {len(prior_attempts) + 1}", flush=True)
            row = benchmark.run_one(
                scenario,
                "with-sidecar",
                trial,
                "diagnostic-v1.7.1",
                plan,
            )
            row["diagnostic_condition"] = CANDIDATE
            row["skill_version"] = "1.7.1"
            row["remediation_attempt"] = len(prior_attempts) + 1
            attempts.append(row)
            if _valid(row):
                valid_keys.add(key)
                consecutive_timeouts = 0
            else:
                total_invalid += 1
                consecutive_timeouts = consecutive_timeouts + 1 if row.get("host_timed_out") else 0
            report = _build_report(plan, source, attempts, preflight, stopped_early)
            _write(report)
            print(
                f"  valid={_valid(row)} verified={row['verified']} "
                f"affected={_affected(row)} tokens={row['model_input_tokens']} "
                f"ms={row['wall_clock_ms']}",
                flush=True,
            )

    report = _build_report(plan, source, attempts, preflight, stopped_early)
    _write(report)
    print(
        f"saved {OUTPUT_PATH} complete={report['complete']} "
        f"safety={report['safety_status']} efficiency={report['efficiency_status']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
