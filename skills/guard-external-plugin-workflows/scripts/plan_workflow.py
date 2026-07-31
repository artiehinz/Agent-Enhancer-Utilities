#!/usr/bin/env python3
"""Deterministic local reference planner for guarded external-plugin work."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


OPERATION_CLASSES = {"read", "create", "update", "send", "delete", "refresh", "batch"}
ITEM_OPERATION_CLASSES = OPERATION_CLASSES - {"batch"}
DUPLICATE_HARM = {"none", "low", "material", "irreversible"}
PROVIDER_IDEMPOTENCY = {"none", "request_key", "atomic_unique_constraint"}
DESTINATION_SEARCH = {"none", "eventual", "strong"}
COMPENSATION = {"none", "reversible", "manual"}
WRITE_OPERATIONS = {"create", "update", "send", "delete"}
PROFILES = {
    "create-once",
    "update-safely",
    "send-at-most-once",
    "refresh-if-stale",
    "fan-out-bounded",
    "scheduled-run",
}
REQUIRED_FIELDS = {
    "contract_version",
    "operation_class",
    "item_operation_class",
    "duplicate_harm",
    "parallel_workers",
    "scheduled",
    "retry_possible",
    "provider_idempotency",
    "destination_search",
    "stable_marker",
    "conditional_write",
    "read_after_write",
    "delivery_status",
    "compensation",
    "shared_rate_limit",
    "maximum_concurrency",
    "freshness_required",
}


class PlannerError(ValueError):
    """Typed planner validation or abstention error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _require_enum(contract: dict[str, Any], field: str, allowed: set[str]) -> None:
    if contract[field] not in allowed:
        raise PlannerError("INVALID_INPUT", f"{field} must be one of {sorted(allowed)}")


def validate_contract(contract: Any) -> dict[str, Any]:
    if not isinstance(contract, dict):
        raise PlannerError("INVALID_INPUT", "input must be one JSON object")
    supplied = set(contract)
    missing = REQUIRED_FIELDS - supplied
    extra = supplied - REQUIRED_FIELDS
    if missing:
        raise PlannerError("INVALID_INPUT", f"missing required fields: {sorted(missing)}")
    if extra:
        raise PlannerError("INVALID_INPUT", f"unknown fields: {sorted(extra)}")
    if contract["contract_version"] != "1":
        raise PlannerError("INVALID_INPUT", "contract_version must be '1'")

    _require_enum(contract, "operation_class", OPERATION_CLASSES)
    _require_enum(contract, "duplicate_harm", DUPLICATE_HARM)
    _require_enum(contract, "provider_idempotency", PROVIDER_IDEMPOTENCY)
    _require_enum(contract, "destination_search", DESTINATION_SEARCH)
    _require_enum(contract, "compensation", COMPENSATION)

    item_operation = contract["item_operation_class"]
    if contract["operation_class"] == "batch":
        if item_operation not in ITEM_OPERATION_CLASSES:
            raise PlannerError(
                "INVALID_INPUT",
                "item_operation_class must be non-null for a batch",
            )
    elif item_operation is not None:
        raise PlannerError(
            "INVALID_INPUT",
            "item_operation_class must be null unless operation_class is batch",
        )

    for field in (
        "scheduled",
        "retry_possible",
        "stable_marker",
        "conditional_write",
        "read_after_write",
        "delivery_status",
        "shared_rate_limit",
        "freshness_required",
    ):
        if not isinstance(contract[field], bool):
            raise PlannerError("INVALID_INPUT", f"{field} must be boolean")

    workers = contract["parallel_workers"]
    if not _is_integer(workers) or not 1 <= workers <= 100:
        raise PlannerError("INVALID_INPUT", "parallel_workers must be an integer from 1 to 100")
    concurrency = contract["maximum_concurrency"]
    if concurrency is not None and (
        not _is_integer(concurrency) or not 1 <= concurrency <= 100
    ):
        raise PlannerError(
            "INVALID_INPUT",
            "maximum_concurrency must be null or an integer from 1 to 100",
        )
    if concurrency is not None and concurrency > workers:
        raise PlannerError(
            "INVALID_INPUT",
            "maximum_concurrency cannot exceed parallel_workers",
        )
    return contract


def effective_operation(contract: dict[str, Any]) -> str:
    if contract["operation_class"] == "batch":
        return contract["item_operation_class"]
    return contract["operation_class"]


def _eligible(contract: dict[str, Any]) -> bool:
    return any(
        (
            contract["parallel_workers"] > 1,
            contract["scheduled"],
            contract["retry_possible"],
            contract["shared_rate_limit"],
            contract["freshness_required"],
            contract["duplicate_harm"] in {"material", "irreversible"},
        )
    )


def requires_workflow_checkpoint(contract: dict[str, Any]) -> bool:
    return (
        effective_operation(contract) in WRITE_OPERATIONS
        and contract["provider_idempotency"] == "none"
        and (
            contract["duplicate_harm"] in {"material", "irreversible"}
            or contract["parallel_workers"] > 1
            or contract["retry_possible"]
            or contract["scheduled"]
        )
    )


def select_profiles(contract: dict[str, Any]) -> tuple[str, list[str]]:
    operation = effective_operation(contract)
    if operation == "create":
        primary = "create-once"
    elif operation == "update":
        primary = "update-safely"
    elif operation in {"send", "delete"}:
        primary = "send-at-most-once"
    elif operation == "refresh" or (
        operation == "read" and contract["freshness_required"]
    ):
        primary = "refresh-if-stale"
    elif operation == "read" and (
        contract["parallel_workers"] > 1 or contract["shared_rate_limit"]
    ):
        primary = "fan-out-bounded"
    elif contract["scheduled"]:
        primary = "scheduled-run"
    else:
        raise PlannerError(
            "UNSUPPORTED_PROFILE",
            "no current profile safely describes this operation",
        )

    additional: list[str] = []
    if contract["operation_class"] == "batch" and primary != "fan-out-bounded":
        additional.append("fan-out-bounded")
    if contract["scheduled"] and primary != "scheduled-run":
        additional.append("scheduled-run")
    return primary, additional


def select_guarantee(contract: dict[str, Any], primary: str) -> str:
    operation = effective_operation(contract)
    if (
        operation in WRITE_OPERATIONS
        and contract["provider_idempotency"] != "none"
    ):
        return "provider-idempotent"
    if operation == "create":
        if (
            contract["stable_marker"]
            and contract["destination_search"] != "none"
            and contract["read_after_write"]
        ):
            return "duplicate-resistant"
        if (
            contract["parallel_workers"] > 1
            and not contract["scheduled"]
            and not contract["retry_possible"]
        ):
            return "concurrency-safe"
        return "best-effort"
    if operation == "update":
        return "concurrency-safe"
    if operation in {"send", "delete"}:
        if contract["delivery_status"]:
            return "duplicate-resistant"
        if contract["retry_possible"] or contract["duplicate_harm"] == "irreversible":
            return "best-effort"
        return "concurrency-safe"
    if primary == "refresh-if-stale":
        return "concurrency-safe"
    if primary == "fan-out-bounded" or contract["shared_rate_limit"]:
        return "rate/concurrency-bounded"
    return "best-effort"


def build_stages(
    contract: dict[str, Any],
    primary: str,
    additional: list[str],
) -> list[dict[str, Any]]:
    stages: list[dict[str, Any]] = []

    def add(actor: str, action: str, candidate_tool: str | None = None) -> None:
        stage: dict[str, Any] = {
            "order": len(stages) + 1,
            "actor": actor,
            "action": action,
        }
        if candidate_tool is not None:
            stage["candidate_tool"] = candidate_tool
        stages.append(stage)

    add("caller", "derive_opaque_operation_identity")

    checkpoint_required = requires_workflow_checkpoint(contract)
    if not checkpoint_required and (
        primary == "scheduled-run" or "scheduled-run" in additional
    ):
        add("agent-enhancer", "acquire_run_lock", "penny-lock")
    if checkpoint_required:
        add("agent-enhancer", "claim_checkpoint", "workflow-checkpoint")
    elif primary in {"create-once", "update-safely", "send-at-most-once"}:
        add("agent-enhancer", "acquire_lock", "penny-lock")
    elif primary == "refresh-if-stale":
        add("agent-enhancer", "acquire_lease", "freshness-lease")

    uses_fanout = primary == "fan-out-bounded" or "fan-out-bounded" in additional
    if uses_fanout and contract["maximum_concurrency"] is not None:
        add("agent-enhancer", "acquire_semaphore", "swarm-semaphore")
    if contract["shared_rate_limit"]:
        add("agent-enhancer", "consume_rate_gate", "swarm-rate-gate")

    operation = effective_operation(contract)

    def start_external_attempt() -> None:
        if checkpoint_required:
            add(
                "agent-enhancer",
                "mark_external_attempt_started",
                "workflow-checkpoint",
            )

    def record_uncertainty_branch() -> None:
        if checkpoint_required:
            add(
                "agent-enhancer",
                "record_external_result_uncertain_if_response_lost",
                "workflow-checkpoint",
            )

    def record_verified() -> None:
        if checkpoint_required:
            add(
                "agent-enhancer",
                "record_caller_verified",
                "workflow-checkpoint",
            )

    if operation == "create":
        if contract["stable_marker"] and contract["destination_search"] != "none":
            add("external-plugin", "search_stable_marker")
        start_external_attempt()
        add("external-plugin", "create")
        record_uncertainty_branch()
        if contract["read_after_write"]:
            add("external-plugin", "read_after_write")
            record_verified()
            add(
                "agent-enhancer",
                "mark_seen_after_verification",
                "global-seen-stamp",
            )
    elif operation == "update":
        add("external-plugin", "read_current_version")
        start_external_attempt()
        add("external-plugin", "apply_update")
        record_uncertainty_branch()
        if contract["read_after_write"]:
            add("external-plugin", "read_after_write")
            record_verified()
    elif operation == "send":
        if contract["delivery_status"]:
            add("external-plugin", "query_delivery_status")
        start_external_attempt()
        add("external-plugin", "send")
        record_uncertainty_branch()
        if contract["delivery_status"]:
            add("external-plugin", "query_delivery_status")
            record_verified()
    elif operation == "delete":
        start_external_attempt()
        add("external-plugin", "delete")
        record_uncertainty_branch()
        if contract["delivery_status"]:
            add("external-plugin", "query_delivery_status")
            record_verified()
    elif operation == "refresh":
        add("external-plugin", "refresh")
        add("external-plugin", "read")
    else:
        add("external-plugin", "read")

    if uses_fanout:
        add("agent-enhancer", "arrive_barrier", "barrier-bell")
    add("caller", "report_outcome")
    return stages


def select_timeout_recovery(contract: dict[str, Any]) -> str:
    operation = effective_operation(contract)
    if requires_workflow_checkpoint(contract):
        if (
            operation == "create"
            and contract["stable_marker"]
            and contract["destination_search"] != "none"
        ):
            return "checkpoint_uncertain_then_search_marker"
        if operation in {"send", "delete"} and contract["delivery_status"]:
            return "checkpoint_uncertain_then_query_delivery"
        return "checkpoint_uncertain_then_stop_for_review"
    if operation == "create":
        if contract["stable_marker"] and contract["destination_search"] != "none":
            return "search_marker_then_bounded_recheck"
        return "stop_for_review"
    if operation in {"send", "delete"}:
        if contract["delivery_status"]:
            return "query_delivery_then_stop_if_uncertain"
        return "stop_for_review"
    if operation == "update":
        return "re_read_then_replan"
    if operation in {"read", "refresh"}:
        return "retry_safe_external_read"
    return "stop_for_review"


def collect_findings(
    contract: dict[str, Any],
    stages: list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    operation = effective_operation(contract)
    residual: list[str] = []
    unsupported = ["sidecar_state_proves_external_completion"]

    if operation in WRITE_OPERATIONS:
        residual.append("no_cross_plugin_transaction")
        unsupported.append("cross_plugin_exactly_once")
    if contract["destination_search"] == "eventual":
        residual.append("destination_search_is_eventually_consistent")
    if any(stage["action"] == "acquire_lock" for stage in stages):
        residual.append("lock_has_bounded_ttl")
    if any(stage["action"] == "mark_seen_after_verification" for stage in stages):
        residual.append("seen_stamp_is_advisory")
    if operation == "update" and not contract["conditional_write"]:
        residual.append("unguarded_writer_can_bypass_sidecar")
    if (
        operation in WRITE_OPERATIONS
        and not contract["read_after_write"]
        and not contract["delivery_status"]
        and contract["provider_idempotency"] == "none"
    ):
        residual.append("external_result_may_be_uncertain")
    if (
        operation in {"send", "delete"}
        and contract["provider_idempotency"] == "none"
        and not contract["delivery_status"]
    ):
        residual.append("uncertain_irreversible_action_requires_review")
    if contract["shared_rate_limit"]:
        unsupported.append("rate_gate_is_action_budget")

    return list(dict.fromkeys(residual)), list(dict.fromkeys(unsupported))


def plan_workflow(raw_contract: Any) -> dict[str, Any]:
    contract = validate_contract(raw_contract)
    if not _eligible(contract):
        return {
            "valid": True,
            "decision": "no-sidecar",
            "decision_reason": "ordinary-one-time-low-risk",
            "profile": None,
            "additional_profiles": [],
            "guarantee": None,
            "stages": [],
            "timeout_recovery": None,
            "residual_risks": [],
            "unsupported_claims": [],
        }
    primary, additional = select_profiles(contract)
    stages = build_stages(contract, primary, additional)
    guarantee = select_guarantee(contract, primary)
    residual, unsupported = collect_findings(contract, stages)
    return {
        "valid": True,
        "decision": "sidecar",
        "decision_reason": "reliability-guard-required",
        "profile": primary,
        "additional_profiles": additional,
        "guarantee": guarantee,
        "stages": stages,
        "timeout_recovery": select_timeout_recovery(contract),
        "residual_risks": residual,
        "unsupported_claims": unsupported,
    }


def _read_input(path: str) -> Any:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Produce a deterministic dry-run sidecar guard plan.",
    )
    parser.add_argument(
        "--input",
        default="-",
        help="Path to a reliability-contract JSON file, or - for stdin.",
    )
    args = parser.parse_args()
    try:
        result = plan_workflow(_read_input(args.input))
    except (json.JSONDecodeError, OSError) as exc:
        result = {
            "valid": False,
            "error": {"code": "INVALID_INPUT", "message": str(exc)},
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2
    except PlannerError as exc:
        result = {
            "valid": False,
            "error": {"code": exc.code, "message": exc.message},
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
