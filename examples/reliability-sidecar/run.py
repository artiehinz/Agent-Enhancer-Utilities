#!/usr/bin/env python3
"""Compose a mock domain agent with the live workflow guard planner."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.mcp_client import McpClient, McpError  # noqa: E402


MCP_URL = os.environ.get(
    "AGENT_ENHANCER_MCP_URL",
    "https://liberated.site/mcp?source=github-example-sidecar",
)

CONTRACT = {
    "contract_version": "1",
    "operation_class": "create",
    "item_operation_class": None,
    "duplicate_harm": "material",
    "parallel_workers": 2,
    "scheduled": False,
    "retry_possible": True,
    "provider_idempotency": "none",
    "destination_search": "strong",
    "stable_marker": True,
    "conditional_write": False,
    "read_after_write": True,
    "delivery_status": False,
    "compensation": "manual",
    "shared_rate_limit": False,
    "maximum_concurrency": 2,
    "freshness_required": False,
}


class MockDomainAgent:
    """A tiny stand-in for a searchable create tool owned by another agent."""

    def __init__(self) -> None:
        self.records: dict[str, dict[str, str]] = {}
        self.create_attempts = 0

    def search_marker(self, marker: str) -> dict[str, str] | None:
        return self.records.get(marker)

    def create(self, marker: str) -> dict[str, str]:
        self.create_attempts += 1
        record = {"id": f"record-{self.create_attempts}", "marker": marker}
        self.records[marker] = record
        return record

    def read_back(self, marker: str) -> dict[str, str]:
        return self.records[marker]


def execute_domain_attempt(agent: MockDomainAgent, marker: str) -> str:
    existing = agent.search_marker(marker)
    if existing is not None:
        return "reused-verified-record"
    created = agent.create(marker)
    assert agent.read_back(marker) == created
    return "created-and-verified"


def main() -> int:
    client = McpClient(MCP_URL)
    server = client.initialize()

    matches = client.call_tool(
        "lab.search_tools",
        {
            "intent": (
                "plan a retryable duplicate-sensitive create performed by "
                "another agent"
            )
        },
    )
    if not any(
        item.get("slug") == "workflow-guard-planner"
        for item in matches.get("tools", [])
    ):
        raise McpError("workflow-guard-planner was not discoverable")

    description = client.call_tool(
        "lab.describe_tool",
        {"slug": "workflow-guard-planner"},
    )
    if description.get("tool", {}).get("payment", {}).get("kind") != "free":
        raise McpError("this public example requires the planner to remain free")

    plan = client.invoke_module("workflow-guard-planner", CONTRACT)
    if (
        plan.get("profile") != "create-once"
        or plan.get("guarantee") != "duplicate-resistant"
    ):
        raise McpError(f"unexpected guard plan: {plan}")

    domain_agent = MockDomainAgent()
    marker = "public-example:quarterly-import:2026-Q3"
    first = execute_domain_attempt(domain_agent, marker)
    replay = execute_domain_attempt(domain_agent, marker)
    if len(domain_agent.records) != 1 or domain_agent.create_attempts != 1:
        raise RuntimeError("the mock domain agent created a duplicate record")

    print(
        json.dumps(
            {
                "server": server["serverInfo"],
                "selected_profile": plan["profile"],
                "honest_guarantee": plan["guarantee"],
                "first_attempt": first,
                "replayed_attempt": replay,
                "records_created": domain_agent.create_attempts,
                "residual_risks": plan["residual_risks"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except McpError as exc:
        print(f"example failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
