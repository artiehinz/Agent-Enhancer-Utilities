#!/usr/bin/env python3
"""Race two workers for one live opaque workflow checkpoint."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.mcp_client import McpClient, McpError  # noqa: E402


MCP_URL = os.environ.get(
    "AGENT_ENHANCER_MCP_URL",
    "https://liberated.site/mcp?source=github-example-checkpoint&profile=core",
)


def new_idempotency_key() -> str:
    return f"public_example_{uuid.uuid4().hex}"


def main() -> int:
    client = McpClient(MCP_URL)
    server = client.initialize()

    matches = client.call_tool(
        "lab.search_tools",
        {
            "intent": (
                "claim transition status opaque workflow checkpoint for "
                "concurrent agents and one duplicate-sensitive external action"
            )
        },
    )
    if not any(
        item.get("slug") == "workflow-checkpoint"
        for item in matches.get("tools", [])
    ):
        raise McpError("workflow-checkpoint was not discoverable")

    description = client.call_tool(
        "lab.describe_tool",
        {"slug": "workflow-checkpoint"},
    )
    tool = description.get("tool", {})
    if tool.get("payment", {}).get("kind") != "free":
        raise McpError("this public example requires the checkpoint to remain free")

    workflow_uuid = uuid.uuid4()
    namespace = f"public-example:{workflow_uuid}"
    workflow_key = f"workflow_{workflow_uuid.hex}"
    holders = [
        f"worker_alpha_{uuid.uuid4().hex}",
        f"worker_bravo_{uuid.uuid4().hex}",
    ]

    def claim(holder: str) -> tuple[str, dict[str, object]]:
        result = client.invoke_module(
            "workflow-checkpoint",
            {
                "action": "claim",
                "namespace": namespace,
                "workflow_key": workflow_key,
                "holder": holder,
                "claim_ttl_seconds": 60,
                "state_ttl_seconds": 120,
                "retry_failed": False,
            },
            idempotency_key=new_idempotency_key(),
        )
        return holder, result

    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(claim, holders))

    winners = [(holder, result) for holder, result in claims if result["acquired"]]
    if len(winners) != 1:
        raise RuntimeError(f"expected one checkpoint owner, received {len(winners)}")

    winner, winning_claim = winners[0]

    # This is the only point where the winning worker would call the external
    # domain tool. The public example records a local synthetic result instead.
    domain_actions = [{"synthetic_result": "created-once"}]
    local_hmac_key = secrets.token_bytes(32)
    evidence_digest = hmac.new(
        local_hmac_key,
        b"synthetic-domain-result:created-once",
        hashlib.sha256,
    ).hexdigest()

    transition = client.invoke_module(
        "workflow-checkpoint",
        {
            "action": "transition",
            "namespace": namespace,
            "workflow_key": workflow_key,
            "holder": winner,
            "expected_generation": winning_claim["generation"],
            "from_stage": "claimed",
            "to_stage": "caller_verified",
            "observation_key": f"observation_{uuid.uuid4().hex}",
            "evidence_type": "durable_result_readback",
            "evidence_fingerprint": f"hmac-sha256:{evidence_digest}",
        },
        idempotency_key=new_idempotency_key(),
    )
    status = client.invoke_module(
        "workflow-checkpoint",
        {
            "action": "status",
            "namespace": namespace,
            "workflow_key": workflow_key,
        },
        idempotency_key=new_idempotency_key(),
    )

    if transition.get("stage") != "caller_verified":
        raise RuntimeError(f"unexpected transition result: {transition}")
    if status.get("external_proof") is not False:
        raise RuntimeError("checkpoint state must not claim external proof")
    if len(domain_actions) != 1:
        raise RuntimeError("more than one synthetic domain action was performed")

    print(
        json.dumps(
            {
                "server": server["serverInfo"],
                "checkpoint_version": tool.get("version"),
                "contenders": len(claims),
                "owners": len(winners),
                "synthetic_domain_actions": len(domain_actions),
                "final_stage": status["stage"],
                "external_proof": status["external_proof"],
                "state_ttl_seconds": 120,
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
