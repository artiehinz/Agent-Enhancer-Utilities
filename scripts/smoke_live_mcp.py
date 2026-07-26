#!/usr/bin/env python3
"""Read-only production smoke test for the public progressive MCP surface."""

from __future__ import annotations

import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))

from common.mcp_client import McpClient, McpError  # noqa: E402


MCP_URL = os.environ.get(
    "AGENT_ENHANCER_MCP_URL",
    "https://liberated.site/mcp?source=github-weekly-smoke",
)
EXPECTED_FACADE_TOOLS = {
    "lab.search_tools",
    "lab.describe_tool",
    "lab.invoke_tool",
    "lab.request_capability",
    "lab.get_capability_request",
    "lab.list_tools",
}


def fail(message: str) -> None:
    raise SystemExit(f"error: {message}")


def main() -> int:
    client = McpClient(MCP_URL)
    initialized = client.initialize()
    server_info = initialized.get("serverInfo", {})
    if server_info.get("name") != "site.liberated/agent-utility-lab":
        fail(f"unexpected server identity: {server_info}")

    listed = client.request("tools/list", {})
    tools = listed.get("tools", [])
    actual_names = {tool.get("name") for tool in tools}
    if actual_names != EXPECTED_FACADE_TOOLS:
        fail(
            "progressive facade drifted: "
            f"expected {sorted(EXPECTED_FACADE_TOOLS)}, got {sorted(actual_names)}"
        )

    read_only_tools = {
        "lab.search_tools",
        "lab.describe_tool",
        "lab.get_capability_request",
        "lab.list_tools",
    }
    for tool in tools:
        if tool.get("name") in read_only_tools:
            annotations = tool.get("annotations", {})
            if annotations.get("readOnlyHint") is not True:
                fail(f"{tool.get('name')} lost readOnlyHint=true")

    catalog = client.call_tool("lab.list_tools", {})
    modules = catalog.get("tools", [])
    if len(modules) != 24:
        fail(f"expected 24 public modules, found {len(modules)}")
    if any(item.get("payment", {}).get("kind") != "free" for item in modules):
        fail("one or more public modules no longer report payment.kind=free")

    search = client.call_tool(
        "lab.search_tools",
        {"intent": "plan a duplicate-sensitive external agent workflow"},
    )
    if not any(
        item.get("slug") == "workflow-guard-planner"
        for item in search.get("tools", [])
    ):
        fail("workflow-guard-planner is no longer discoverable")

    description = client.call_tool(
        "lab.describe_tool",
        {"slug": "workflow-guard-planner"},
    )
    if description.get("tool", {}).get("payment", {}).get("kind") != "free":
        fail("workflow-guard-planner is missing or no longer free")

    print(
        "live MCP smoke passed: "
        f"server={server_info.get('version')} "
        f"facade_tools={len(tools)} modules={len(modules)}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except McpError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
