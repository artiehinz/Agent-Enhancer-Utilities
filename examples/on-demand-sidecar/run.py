#!/usr/bin/env python3
"""Activate the existing Agent Enhancer service only after local selection."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
PLANNER_PATH = (
    ROOT
    / "skills"
    / "guard-external-plugin-workflows"
    / "scripts"
    / "plan_workflow.py"
)
PLANNER_SPEC = importlib.util.spec_from_file_location(
    "agent_enhancer_local_planner",
    PLANNER_PATH,
)
if PLANNER_SPEC is None or PLANNER_SPEC.loader is None:
    raise RuntimeError("unable to load the local workflow planner")
LOCAL_PLANNER = importlib.util.module_from_spec(PLANNER_SPEC)
PLANNER_SPEC.loader.exec_module(LOCAL_PLANNER)

DEFAULT_URL = (
    "https://liberated.site/v1/tools/workflow-guard-planner"
    "?source=github-on-demand-sidecar"
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


class PlannerClient(Protocol):
    calls: int

    def plan(self, contract: dict[str, Any]) -> dict[str, Any]:
        """Return the hosted workflow-guard-planner result."""


class DirectPlannerClient:
    """Small no-auth HTTP adapter for the existing hosted planner."""

    def __init__(
        self,
        url: str = DEFAULT_URL,
        timeout_seconds: float = 20.0,
    ) -> None:
        self.url = url
        self.timeout_seconds = timeout_seconds
        self.calls = 0

    def plan(self, contract: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "agent-enhancer-on-demand-example/1.0",
        }
        internal_marker = os.environ.get(
            "AGENT_ENHANCER_INTERNAL_METRICS_TOKEN"
        )
        if internal_marker:
            headers["X-Agent-Internal-Metrics"] = internal_marker
        request = Request(
            self.url,
            data=json.dumps(
                contract,
                separators=(",", ":"),
            ).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"planner returned HTTP {error.code}: {detail}"
            ) from error
        except URLError as error:
            raise RuntimeError(
                f"planner connection failed: {error.reason}"
            ) from error
        if not isinstance(body, dict):
            raise RuntimeError("planner response was not a JSON object")
        result = body.get("result")
        if body.get("ok") is not True or not isinstance(result, dict):
            raise RuntimeError("planner response was not a successful result")
        return result


def plan_on_demand(
    contract: dict[str, Any],
    client: PlannerClient,
) -> dict[str, Any]:
    local = LOCAL_PLANNER.plan_workflow(contract)
    if local["decision"] == "no-sidecar":
        return {
            "decision": "no-sidecar",
            "activation": "local-abstention",
            "remote_calls": client.calls,
            "plan": local,
        }

    remote = client.plan(contract)
    for field in (
        "decision",
        "profile",
        "additional_profiles",
        "guarantee",
        "timeout_recovery",
    ):
        if remote.get(field) != local.get(field):
            raise RuntimeError(
                f"local and hosted planners disagree on {field}"
            )
    return {
        "decision": "sidecar",
        "activation": "remote-after-local-selection",
        "remote_calls": client.calls,
        "plan": remote,
    }


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "both"
    if mode not in {"low-risk", "high-risk", "both"}:
        raise RuntimeError(
            "usage: python run.py [low-risk|high-risk|both]"
        )
    client = DirectPlannerClient(
        os.environ.get("AGENT_ENHANCER_PLANNER_URL", DEFAULT_URL)
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
