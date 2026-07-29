#!/usr/bin/env python3
"""Demonstrate the canonical skills-first on-demand adapter."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
ADAPTER_PATH = (
    ROOT
    / "skills"
    / "guard-external-plugin-workflows"
    / "scripts"
    / "on_demand.py"
)
ADAPTER_SPEC = importlib.util.spec_from_file_location(
    "agent_enhancer_on_demand_adapter",
    ADAPTER_PATH,
)
if ADAPTER_SPEC is None or ADAPTER_SPEC.loader is None:
    raise RuntimeError("unable to load the on-demand adapter")
ADAPTER = importlib.util.module_from_spec(ADAPTER_SPEC)
ADAPTER_SPEC.loader.exec_module(ADAPTER)
LOCAL_PLANNER = ADAPTER.LOCAL_PLANNER
plan_on_demand = ADAPTER.plan_on_demand

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

HIGH_RISK_CONTRACT = {
    **LOW_RISK_CONTRACT,
    "operation_class": "create",
    "duplicate_harm": "material",
    "parallel_workers": 2,
    "retry_possible": True,
    "destination_search": "strong",
    "stable_marker": True,
    "read_after_write": True,
    "compensation": "manual",
    "maximum_concurrency": 2,
}


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "both"
    if mode not in {"low-risk", "high-risk", "both"}:
        raise RuntimeError(
            "usage: python run.py [low-risk|high-risk|both]"
        )
    client = ADAPTER.DirectToolClient(
        os.environ.get(
            "AGENT_ENHANCER_HTTP_BASE_URL",
            ADAPTER.DEFAULT_BASE_URL,
        ),
        source="github-on-demand-sidecar",
    )
    output: dict[str, Any] = {}
    if mode in {"low-risk", "both"}:
        output["low_risk"] = plan_on_demand(
            LOW_RISK_CONTRACT,
            client,
        )
    if mode in {"high-risk", "both"}:
        output["high_risk"] = plan_on_demand(
            HIGH_RISK_CONTRACT,
            client,
        )
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError) as error:
        print(f"example failed: {error}", file=sys.stderr)
        raise SystemExit(1)
