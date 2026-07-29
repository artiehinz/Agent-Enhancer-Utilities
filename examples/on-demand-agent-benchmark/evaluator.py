"""Condition-blind evaluator for metered agent benchmark workspaces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def evaluate_workspace(
    workspace: Path,
    scenario: str,
    final_response: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate destination state without receiving the condition label."""
    state = _load_json(workspace / ".benchmark" / "state.json")
    manual = int(bool(final_response.get("manual_intervention_required", False)))
    base = {
        "verified": False,
        "external_attempts": int(state.get("external_attempts", 0)),
        "duplicate_mutations": int(state.get("duplicate_mutations", 0)),
        "conflicting_actions": 0,
        "provider_rejections": int(state.get("provider_rejections", 0)),
        "unresolved_ambiguous": 0,
        "manual_interventions": manual,
    }

    if state.get("scenario") != scenario:
        base["manual_interventions"] += 1
        return base

    if scenario == "ambiguous-success-create":
        records = [
            record
            for record in state.get("records", [])
            if record.get("marker") == "marker:ambiguous-create"
        ]
        reconciled = int(state.get("reconciliations", 0)) > 0
        unresolved = bool(state.get("uncertain", False)) or not reconciled
        base["unresolved_ambiguous"] = int(unresolved)
        base["verified"] = len(records) == 1 and not unresolved
        return base

    if scenario == "overlapping-workers":
        mutations = [
            mutation
            for mutation in state.get("mutations", [])
            if mutation.get("operation") == "shared-release"
        ]
        base["conflicting_actions"] = max(0, len(mutations) - 1)
        base["verified"] = len(mutations) == 1
        return base

    if scenario == "shared-rate-limit":
        expected = {f"item-{index}" for index in range(1, 11)}
        processed = list(state.get("processed", []))
        base["verified"] = (
            set(processed) == expected
            and len(processed) == len(expected)
            and base["provider_rejections"] == 0
        )
        return base

    if scenario == "scheduled-refresh":
        base["verified"] = (
            int(state.get("current_version", -1)) == 7
            and int(state.get("refreshes", -1)) == 0
            and int(state.get("status_checks", 0)) >= 1
        )
        return base

    if scenario == "low-risk-abstention":
        base["verified"] = (
            str(final_response.get("answer")) == "42"
            and int(state.get("read_calls", 0)) == 1
        )
        return base

    base["manual_interventions"] += 1
    return base
