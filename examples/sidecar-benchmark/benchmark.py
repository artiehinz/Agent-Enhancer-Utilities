"""Deterministic paired fixtures for Reliability Sidecar Contract v1."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import importlib.util
import json
from pathlib import Path
import random
import time
from typing import Any, Callable

from adapters import InMemoryReliabilityAdapter, opaque_id


ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = (
    ROOT
    / "skills"
    / "guard-external-plugin-workflows"
    / "scripts"
    / "plan_workflow.py"
)


def _load_planner() -> Callable[[Any], dict[str, Any]]:
    spec = importlib.util.spec_from_file_location("sidecar_planner", PLAN_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load the local workflow planner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.plan_workflow


PLAN_WORKFLOW = _load_planner()


@dataclass
class Metrics:
    verified: bool
    external_attempts: int = 0
    duplicate_mutations: int = 0
    conflicting_actions: int = 0
    provider_rejections: int = 0
    unresolved_ambiguous: int = 0
    manual_interventions: int = 0
    sidecar_calls: int = 0
    abstained: bool = False
    model_input_tokens: None = None
    model_output_tokens: None = None
    model_cost_usd: None = None
    wall_clock_ms: float = 0.0


class ResponseLost(RuntimeError):
    """Injected after a synthetic destination commits."""


class CreateDestination:
    def __init__(self) -> None:
        self.records: list[dict[str, str]] = []
        self.drop_next_response = True

    def create(self, marker: str) -> dict[str, str]:
        record = {"id": f"record-{len(self.records) + 1}", "marker": marker}
        self.records.append(record)
        if self.drop_next_response:
            self.drop_next_response = False
            raise ResponseLost("synthetic response lost after commit")
        return record

    def search(self, marker: str) -> list[dict[str, str]]:
        return [record for record in self.records if record["marker"] == marker]


def ambiguous_success_create(condition: str) -> Metrics:
    destination = CreateDestination()
    marker = "marker:ambiguous-create"
    adapter = InMemoryReliabilityAdapter()
    operation_id = opaque_id("op", marker)
    holder_id = opaque_id("holder", "worker-primary")
    attempts = 0
    unresolved = 0

    if condition == "without-sidecar":
        try:
            attempts += 1
            destination.create(marker)
        except ResponseLost:
            attempts += 1
            destination.create(marker)
        records = destination.search(marker)
        return Metrics(
            verified=len(records) >= 1,
            external_attempts=attempts,
            duplicate_mutations=max(0, len(records) - 1),
        )

    acquired, checkpoint = adapter.claim(operation_id, holder_id)
    if not acquired:
        raise RuntimeError("first worker did not acquire the checkpoint")
    adapter.transition(operation_id, holder_id, "external_attempt_started")
    try:
        attempts += 1
        destination.create(marker)
    except ResponseLost:
        checkpoint = adapter.transition(
            operation_id,
            holder_id,
            "external_result_uncertain",
        )
        records = destination.search(marker)
        if len(records) == 1:
            checkpoint = adapter.transition(
                operation_id,
                holder_id,
                "caller_verified",
            )
        else:
            unresolved = 1
    records = destination.search(marker)
    return Metrics(
        verified=checkpoint["stage"] == "caller_verified" and len(records) == 1,
        external_attempts=attempts,
        duplicate_mutations=max(0, len(records) - 1),
        unresolved_ambiguous=unresolved,
        sidecar_calls=adapter.calls,
    )


def overlapping_workers(condition: str) -> Metrics:
    writes: list[str] = []
    adapter = InMemoryReliabilityAdapter()
    operation_id = opaque_id("op", "workspace:shared-change")
    holders = [
        opaque_id("holder", "worker-alpha"),
        opaque_id("holder", "worker-bravo"),
    ]

    if condition == "without-sidecar":
        writes.extend(["patch-alpha", "patch-bravo"])
        return Metrics(
            verified=False,
            external_attempts=2,
            conflicting_actions=1,
        )

    winners = []
    for holder in holders:
        acquired, _ = adapter.claim(operation_id, holder)
        if acquired:
            winners.append(holder)
    if len(winners) != 1:
        raise RuntimeError("expected exactly one admitted worker")
    winner = winners[0]
    adapter.transition(operation_id, winner, "external_attempt_started")
    writes.append("patch-canonical")
    adapter.transition(operation_id, winner, "caller_verified")
    return Metrics(
        verified=writes == ["patch-canonical"],
        external_attempts=1,
        conflicting_actions=0,
        sidecar_calls=adapter.calls,
    )


def shared_rate_limit(condition: str) -> Metrics:
    provider_limit = 5
    provider_calls = 0
    provider_rejections = 0
    admitted = 0
    sidecar_calls = 0
    for index in range(10):
        if condition == "with-sidecar":
            sidecar_calls += 1
            if admitted >= provider_limit:
                continue
            admitted += 1
        provider_calls += 1
        if provider_calls > provider_limit:
            provider_rejections += 1
    return Metrics(
        verified=provider_rejections == 0,
        external_attempts=provider_calls,
        provider_rejections=provider_rejections,
        sidecar_calls=sidecar_calls,
    )


def scheduled_refresh(condition: str) -> Metrics:
    refreshes = 0
    is_fresh = False
    sidecar_calls = 0
    for _ in range(2):
        if condition == "with-sidecar":
            sidecar_calls += 1
            if is_fresh:
                continue
        refreshes += 1
        is_fresh = True
    return Metrics(
        verified=is_fresh,
        external_attempts=refreshes,
        duplicate_mutations=max(0, refreshes - 1),
        sidecar_calls=sidecar_calls,
    )


LOW_RISK_CONTRACT = {
    "contract_version": "1",
    "operation_class": "read",
    "item_operation_class": None,
    "duplicate_harm": "none",
    "parallel_workers": 1,
    "scheduled": False,
    "retry_possible": False,
    "provider_idempotency": "none",
    "destination_search": "none",
    "stable_marker": False,
    "conditional_write": False,
    "read_after_write": False,
    "delivery_status": False,
    "compensation": "none",
    "shared_rate_limit": False,
    "maximum_concurrency": None,
    "freshness_required": False,
}


def low_risk_abstention(condition: str) -> Metrics:
    abstained = False
    if condition == "with-sidecar":
        plan = PLAN_WORKFLOW(LOW_RISK_CONTRACT)
        if plan["decision"] != "no-sidecar":
            raise RuntimeError("planner failed to abstain from a low-risk read")
        abstained = True
    return Metrics(
        verified=True,
        external_attempts=1,
        sidecar_calls=0,
        abstained=abstained,
    )


SCENARIOS: dict[str, Callable[[str], Metrics]] = {
    "ambiguous-success-create": ambiguous_success_create,
    "overlapping-workers": overlapping_workers,
    "shared-rate-limit": shared_rate_limit,
    "scheduled-refresh": scheduled_refresh,
    "low-risk-abstention": low_risk_abstention,
}

RUN_COLUMNS = [
    "scenario",
    "condition",
    "pair",
    "phase",
    "verified",
    "external_attempts",
    "duplicate_mutations",
    "conflicting_actions",
    "provider_rejections",
    "unresolved_ambiguous",
    "manual_interventions",
    "sidecar_calls",
    "abstained",
    "model_input_tokens",
    "model_output_tokens",
    "model_cost_usd",
    "wall_clock_ms",
]


def timed_run(
    scenario: str,
    condition: str,
    pair: int,
    phase: str,
) -> dict[str, Any]:
    started = time.perf_counter_ns()
    metrics = SCENARIOS[scenario](condition)
    metrics.wall_clock_ms = round(
        (time.perf_counter_ns() - started) / 1_000_000,
        6,
    )
    return {
        "scenario": scenario,
        "condition": condition,
        "pair": pair,
        "phase": phase,
        **asdict(metrics),
    }


def aggregate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for scenario in SCENARIOS:
        for condition in ("without-sidecar", "with-sidecar"):
            selected = [
                row
                for row in rows
                if row["scenario"] == scenario
                and row["condition"] == condition
            ]
            output.append(
                {
                    "scenario": scenario,
                    "condition": condition,
                    "runs": len(selected),
                    "verified_runs": sum(bool(row["verified"]) for row in selected),
                    "external_attempts": sum(row["external_attempts"] for row in selected),
                    "duplicate_mutations": sum(
                        row["duplicate_mutations"] for row in selected
                    ),
                    "conflicting_actions": sum(
                        row["conflicting_actions"] for row in selected
                    ),
                    "provider_rejections": sum(
                        row["provider_rejections"] for row in selected
                    ),
                    "unresolved_ambiguous": sum(
                        row["unresolved_ambiguous"] for row in selected
                    ),
                    "manual_interventions": sum(
                        row["manual_interventions"] for row in selected
                    ),
                    "sidecar_calls": sum(row["sidecar_calls"] for row in selected),
                    "model_input_tokens": None,
                    "model_output_tokens": None,
                    "model_cost_usd": None,
                    "wall_clock_ms_total": round(
                        sum(row["wall_clock_ms"] for row in selected),
                        6,
                    ),
                }
            )
    return output


def evaluate(
    aggregates: list[dict[str, Any]],
    thresholds: dict[str, Any],
) -> dict[str, Any]:
    def selected(condition: str) -> list[dict[str, Any]]:
        return [
            row
            for row in aggregates
            if row["condition"] == condition
        ]

    unguarded = selected("without-sidecar")
    guarded = selected("with-sidecar")
    harmful_fields = (
        "duplicate_mutations",
        "conflicting_actions",
        "provider_rejections",
        "unresolved_ambiguous",
    )
    unguarded_harm = sum(
        sum(int(row[field]) for field in harmful_fields)
        for row in unguarded
    )
    guarded_harm = sum(
        sum(int(row[field]) for field in harmful_fields)
        for row in guarded
    )
    harm_reduction = (
        100.0
        if unguarded_harm > 0 and guarded_harm == 0
        else round(
            ((unguarded_harm - guarded_harm) / unguarded_harm) * 100,
            1,
        )
        if unguarded_harm > 0
        else 0.0
    )
    guarded_verified = sum(int(row["verified_runs"]) for row in guarded)
    unguarded_verified = sum(int(row["verified_runs"]) for row in unguarded)
    guarded_runs = sum(int(row["runs"]) for row in guarded)
    unguarded_runs = sum(int(row["runs"]) for row in unguarded)
    verified_drop = round(
        (unguarded_verified / unguarded_runs) * 100
        - (guarded_verified / guarded_runs) * 100,
        1,
    )
    low_risk = next(
        row
        for row in guarded
        if row["scenario"] == "low-risk-abstention"
    )
    checks = {
        "harm_reduction": (
            harm_reduction
            >= thresholds["failure_scenario_harm_reduction_percent"]
        ),
        "verified_completion": (
            verified_drop
            <= thresholds[
                "maximum_verified_completion_drop_percentage_points"
            ]
        ),
        "low_risk_abstention": (
            low_risk["sidecar_calls"]
            == thresholds["low_risk_sidecar_calls"]
        ),
    }
    return {
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "observed": {
            "unguarded_harmful_events": unguarded_harm,
            "guarded_harmful_events": guarded_harm,
            "harm_reduction_percent": harm_reduction,
            "unguarded_verified_rate_percent": round(
                (unguarded_verified / unguarded_runs) * 100,
                1,
            ),
            "guarded_verified_rate_percent": round(
                (guarded_verified / guarded_runs) * 100,
                1,
            ),
            "verified_completion_drop_percentage_points": verified_drop,
            "low_risk_sidecar_calls": low_risk["sidecar_calls"],
        },
    }


def build_report(plan: dict[str, Any]) -> dict[str, Any]:
    randomizer = random.Random(plan["seed"])
    validation_rows = []
    published_rows = []
    for scenario in SCENARIOS:
        for pair in range(1, plan["validation_pairs_per_scenario"] + 1):
            conditions = ["without-sidecar", "with-sidecar"]
            randomizer.shuffle(conditions)
            for condition in conditions:
                validation_rows.append(
                    timed_run(scenario, condition, pair, "validation")
                )
        for pair in range(1, plan["published_pairs_per_scenario"] + 1):
            conditions = ["without-sidecar", "with-sidecar"]
            randomizer.shuffle(conditions)
            for condition in conditions:
                published_rows.append(
                    timed_run(scenario, condition, pair, "published")
                )
    aggregates = aggregate(published_rows)
    return {
        "schema_version": "1",
        "contract_version": "1",
        "evidence_class": plan["evidence_class"],
        "seed": plan["seed"],
        "validation": {
            "pairs_per_scenario": plan["validation_pairs_per_scenario"],
            "rows_executed": len(validation_rows),
            "included_in_results": False,
        },
        "published": {
            "pairs_per_scenario": plan["published_pairs_per_scenario"],
            "rows": published_rows,
            "aggregates": aggregates,
        },
        "thresholds": plan["success_thresholds"],
        "evaluation": evaluate(aggregates, plan["success_thresholds"]),
        "limitations": plan["limitations"],
        "claims": [
            "Deterministic fixtures measure protocol behavior under injected failures.",
            "No language model was used, so token, model-cost, and agent-quality benefits are not claimed.",
            "Every checkpoint and report in these fixtures has external_proof false.",
        ],
    }


def compact_report(report: dict[str, Any]) -> dict[str, Any]:
    """Return the public report with compact but complete run-level rows."""
    compacted = dict(report)
    published = dict(report["published"])
    published["row_columns"] = RUN_COLUMNS
    published["rows"] = [
        [row[column] for column in RUN_COLUMNS]
        for row in report["published"]["rows"]
    ]
    compacted["published"] = published
    return compacted


def load_plan(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
