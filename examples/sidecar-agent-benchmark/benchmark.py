"""Metered Codex with/without Agent Enhancer benchmark harness."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import statistics
import subprocess
import tempfile
import time
from typing import Any, Iterable

from evaluator import evaluate_workspace


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SCENARIOS = (
    "ambiguous-success-create",
    "overlapping-workers",
    "shared-rate-limit",
    "scheduled-refresh",
    "low-risk-abstention",
)
CONDITIONS = ("without-sidecar", "with-sidecar")
SIDE_EFFECTING_SCENARIOS = set(SCENARIOS) - {"low-risk-abstention"}
PARALLEL_SCENARIOS = {
    "overlapping-workers",
    "shared-rate-limit",
    "scheduled-refresh",
}
INTERNAL_TOKEN_ENV = "AGENT_ENHANCER_INTERNAL_METRICS_TOKEN"
DISCOVERY_SOURCE = "codex-agent-benchmark"
PROTOCOL_FILES = (
    "preregistered-plan.json",
    "benchmark.py",
    "evaluator.py",
    "fixture_cli.py",
    "final-response.schema.json",
)


COMMON_PROMPT = """\
You are executing one isolated run in a controlled reliability study.
Work only inside the current workspace. Do not browse the web.

The exact same task is used whether or not an optional MCP server named
`agent_enhancer` is available. If it is available, consult it only when the
task has a real coordination, retry, freshness, or ambiguous-success risk.
For a side-effecting scenario, start `lab.search_tools` with the exact intent
`workflow guard planner` and no category filter, then use `lab.describe_tool`
and `lab.invoke_tool` on the returned `workflow-guard-planner` slug. Discover
an additional coordination primitive only when that guard plan recommends
one. Do not call `lab.request_capability` in this study. Send only opaque
benchmark identifiers. Never send file contents, credentials, or destination
payloads to the sidecar. If the server is absent, continue with your best
normal workflow.

Generic execution policy: independent work may run concurrently and a clearly
transient failure may be retried once. An error that might have happened after
a write committed is not proof of failure; reconcile it before deciding
whether another mutation is safe.

Use only `python fixture_cli.py ...` to interact with the synthetic
destination. Do not read or edit `.benchmark/state.json` directly. You may
inspect command help with `python fixture_cli.py --help`.
"""


PROMPTS = {
    "ambiguous-success-create": """\
Create exactly one external ticket with marker `marker:ambiguous-create`.
The destination may lose a response after committing the write. Finish only
after reconciling the marker through the destination. There must be exactly
one ticket, never two.

Commands:
- `python fixture_cli.py ambiguous-create --marker marker:ambiguous-create`
- `python fixture_cli.py ambiguous-find --marker marker:ambiguous-create`
""",
    "overlapping-workers": """\
Use exactly two subagents concurrently, identified as `alpha` and `bravo`.
Give both the same goal: ensure the external operation `shared-release` is
applied. Both workers must participate, but the duplicate-sensitive provider
mutation must cross the boundary exactly once. Use shared coordination if it
is available; do not serialize the two workers merely to avoid the test.

Each admitted worker uses:
`python fixture_cli.py overlap-apply --operation shared-release --worker NAME`
""",
    "shared-rate-limit": """\
Use exactly two subagents concurrently. Split items `item-1` through `item-10`
between them and process every item exactly once. The provider publishes one
shared limit of five accepted calls per window across both workers. Advance
the window only after five accepted calls. Do not generate a provider 429.

Commands:
- `python fixture_cli.py provider-call --item item-N`
- `python fixture_cli.py provider-next-window`
""",
    "scheduled-refresh": """\
Use exactly two subagents concurrently, representing two scheduler workers.
Both must independently decide whether dataset version 7 needs refresh.
Suppress stale or duplicate work: if version 7 is already current, neither
worker should refresh it.

Commands:
- `python fixture_cli.py refresh-status`
- `python fixture_cli.py refresh-apply --version 7`
""",
    "low-risk-abstention": """\
This is an ordinary one-time, read-only lookup. Read the fixture fact exactly
once with `python fixture_cli.py read-fact` and return the value as `answer`.
Do not invoke a reliability sidecar for this low-risk read.
""",
}


def load_plan(path: Path | None = None) -> dict[str, Any]:
    selected = path or HERE / "preregistered-plan.json"
    return json.loads(selected.read_text(encoding="utf-8"))


def protocol_sha256() -> str:
    digest = hashlib.sha256()
    for relative_path in PROTOCOL_FILES:
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        content = (HERE / relative_path).read_bytes()
        digest.update(content.replace(b"\r\n", b"\n").replace(b"\r", b"\n"))
        digest.update(b"\0")
    return digest.hexdigest()


def _opaque_run_id(scenario: str, pair: int, phase: str) -> str:
    digest = hashlib.sha256(
        f"{scenario}:{pair}:{phase}".encode("utf-8")
    ).hexdigest()[:16]
    return f"bench-{digest}"


def _initialize_workspace(workspace: Path, scenario: str) -> None:
    shutil.copy2(HERE / "fixture_cli.py", workspace / "fixture_cli.py")
    result = subprocess.run(
        ["python", "fixture_cli.py", "init", scenario],
        cwd=workspace,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"fixture initialization failed: {result.stderr.strip()}"
        )


def _codex_command(
    workspace: Path,
    condition: str,
    plan: dict[str, Any],
) -> list[str]:
    command = [
        str(plan["host"]["executable"]),
        "exec",
        "--json",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--skip-git-repo-check",
        "--sandbox",
        str(plan["host"]["sandbox"]),
        "--model",
        str(plan["host"]["model"]),
        "-c",
        'approval_policy="never"',
        "-c",
        f'model_reasoning_effort="{plan["host"]["reasoning_effort"]}"',
        "-c",
        "features.apps=false",
        "-C",
        str(workspace),
        "--output-schema",
        str(HERE / "final-response.schema.json"),
    ]
    if condition == "with-sidecar":
        command.extend(
            [
                "-c",
                (
                    "mcp_servers.agent_enhancer.url="
                    f'"{plan["host"]["agent_enhancer_endpoint"]}"'
                ),
                "-c",
                "mcp_servers.agent_enhancer.required=true",
                "-c",
                (
                    "mcp_servers.agent_enhancer.env_http_headers="
                    "{x-agent-internal-metrics="
                    f'"{INTERNAL_TOKEN_ENV}"'
                    "}"
                ),
                "-c",
                (
                    "mcp_servers.agent_enhancer.http_headers="
                    "{x-agent-discovery-source="
                    f'"{DISCOVERY_SOURCE}"'
                    "}"
                ),
            ]
        )
    return command


def _parse_jsonl(output: str) -> tuple[list[dict[str, Any]], list[str]]:
    events: list[dict[str, Any]] = []
    invalid: list[str] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            invalid.append(line)
            continue
        if isinstance(parsed, dict):
            events.append(parsed)
    return events, invalid


def _completed_items(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        event.get("item", {})
        for event in events
        if event.get("type") == "item.completed"
        and isinstance(event.get("item"), dict)
    ]


def _final_response(items: list[dict[str, Any]]) -> dict[str, Any]:
    messages = [
        item.get("text", "")
        for item in items
        if item.get("type") == "agent_message"
    ]
    for text in reversed(messages):
        try:
            parsed = json.loads(text)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(parsed, dict):
            return parsed
    return {}


def _usage(events: list[dict[str, Any]]) -> dict[str, int]:
    completed = next(
        (
            event
            for event in reversed(events)
            if event.get("type") == "turn.completed"
        ),
        {},
    )
    usage = completed.get("usage", {})
    if not isinstance(usage, dict):
        usage = {}
    return {
        "model_input_tokens": int(usage.get("input_tokens", 0)),
        "model_cached_input_tokens": int(
            usage.get("cached_input_tokens", 0)
        ),
        "model_output_tokens": int(usage.get("output_tokens", 0)),
        "model_reasoning_output_tokens": int(
            usage.get("reasoning_output_tokens", 0)
        ),
    }


def _tool_metrics(items: list[dict[str, Any]]) -> dict[str, Any]:
    item_types = Counter(str(item.get("type", "unknown")) for item in items)
    mcp_calls = [
        item
        for item in items
        if item.get("type") == "mcp_tool_call"
        and item.get("server") == "agent_enhancer"
    ]
    invocation_calls = [
        item
        for item in mcp_calls
        if item.get("tool") == "lab.invoke_tool"
        or (
            item.get("tool") == "lab.sidecar"
            and isinstance(item.get("arguments"), dict)
            and item["arguments"].get("op") == "invoke"
        )
    ]
    def marker_acknowledged(item: dict[str, Any]) -> bool:
        result = item.get("result")
        if not isinstance(result, dict):
            return False
        structured = (
            result.get("structured_content")
            or result.get("structuredContent")
        )
        if not isinstance(structured, dict):
            return False
        if structured.get("owned_automation_excluded") is True:
            return True
        execution = structured.get("execution")
        return bool(
            isinstance(execution, dict)
            and execution.get("owned_automation_excluded") is True
        )

    call_marker_acknowledgements = sum(
        int(marker_acknowledged(item)) for item in mcp_calls
    )
    invocation_marker_acknowledgements = sum(
        int(marker_acknowledged(item)) for item in invocation_calls
    )
    fingerprints = [
        json.dumps(
            {
                "tool": item.get("tool"),
                "arguments": item.get("arguments"),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        for item in mcp_calls
    ]
    return {
        "agent_item_counts": dict(sorted(item_types.items())),
        "collab_tool_calls": int(item_types.get("collab_tool_call", 0)),
        "agent_tool_calls": sum(
            count
            for kind, count in item_types.items()
            if kind
            not in {
                "agent_message",
                "reasoning",
            }
        ),
        "sidecar_calls": len(mcp_calls),
        "sidecar_invoke_calls": len(invocation_calls),
        "owned_automation_call_acknowledgements": (
            call_marker_acknowledgements
        ),
        "owned_automation_marker_acknowledgements": (
            invocation_marker_acknowledgements
        ),
        "unmarked_sidecar_invocations": (
            len(invocation_calls) - invocation_marker_acknowledgements
        ),
        "repeated_sidecar_calls": sum(
            count - 1
            for count in Counter(fingerprints).values()
            if count > 1
        ),
        "unexpected_mcp_calls": sum(
            1
            for item in items
            if item.get("type") == "mcp_tool_call"
            and item.get("server") != "agent_enhancer"
        ),
        "unexpected_mcp_servers": sorted(
            {
                str(item.get("server"))
                for item in items
                if item.get("type") == "mcp_tool_call"
                and item.get("server") != "agent_enhancer"
            }
        ),
        "sidecar_tools": sorted(
            {
                str(item.get("tool"))
                for item in mcp_calls
                if item.get("tool")
            }
        ),
    }


def verify_owned_automation_marker(
    plan: dict[str, Any],
) -> dict[str, int]:
    """Prove that Codex transports the marker and production accepts it."""
    if not os.environ.get(INTERNAL_TOKEN_ENV):
        raise RuntimeError(
            f"{INTERNAL_TOKEN_ENV} must mark owned production traffic"
        )
    compact = "profile=compact" in str(
        plan["host"]["agent_enhancer_endpoint"]
    )
    tool_instruction = (
        "Call agent_enhancer lab.sidecar exactly once with arguments "
        '{"op":"search","intent":"workflow guard planner"}'
        if compact
        else "Call agent_enhancer lab.search_tools exactly once with "
        'arguments {"intent":"workflow guard planner"}'
    )
    prompt = (
        tool_instruction
        + ". Do not call another tool. Return completed=true, answer=null, "
        'verification="marker preflight", and '
        "manual_intervention_required=false."
    )
    try:
        with tempfile.TemporaryDirectory(
            prefix="agent-sidecar-marker-preflight-"
        ) as temporary:
            workspace = Path(temporary)
            completed = subprocess.run(
                [
                    *_codex_command(workspace, "with-sidecar", plan),
                    prompt,
                ],
                cwd=workspace,
                env=os.environ.copy(),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=int(plan["host"]["timeout_seconds"]),
                check=False,
            )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(
            "owned-automation marker preflight timed out; "
            "no benchmark runs were started"
        ) from error
    events, invalid_jsonl = _parse_jsonl(completed.stdout)
    items = _completed_items(events)
    metrics = _tool_metrics(items)
    event_errors = [
        event
        for event in events
        if event.get("type") in {"error", "turn.failed"}
    ]
    if (
        completed.returncode != 0
        or invalid_jsonl
        or event_errors
        or int(metrics["sidecar_calls"]) != 1
        or int(metrics["sidecar_invoke_calls"]) != 0
        or int(
            metrics["owned_automation_call_acknowledgements"]
        )
        != 1
    ):
        raise RuntimeError(
            "owned-automation marker preflight failed through Codex; "
            "no benchmark runs were started"
        )
    usage = _usage(events)
    return {
        "sidecar_calls": int(metrics["sidecar_calls"]),
        "owned_automation_call_acknowledgements": int(
            metrics["owned_automation_call_acknowledgements"]
        ),
        "model_input_tokens": usage["model_input_tokens"],
        "model_output_tokens": usage["model_output_tokens"],
    }


def run_one(
    scenario: str,
    condition: str,
    pair: int,
    phase: str,
    plan: dict[str, Any],
    keep_workspace: Path | None = None,
) -> dict[str, Any]:
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario: {scenario}")
    if condition not in CONDITIONS:
        raise ValueError(f"unknown condition: {condition}")
    if condition == "with-sidecar" and not os.environ.get(INTERNAL_TOKEN_ENV):
        raise RuntimeError(
            f"{INTERNAL_TOKEN_ENV} must mark owned production traffic"
        )

    temporary = tempfile.TemporaryDirectory(prefix="agent-sidecar-benchmark-")
    workspace = Path(temporary.name)
    _initialize_workspace(workspace, scenario)
    prompt = (
        COMMON_PROMPT
        + "\nOpaque run identifier: `"
        + _opaque_run_id(scenario, pair, phase)
        + "`.\n\n"
        + PROMPTS[scenario]
    )
    command = _codex_command(workspace, condition, plan)
    started = time.perf_counter()
    timed_out = False
    try:
        completed = subprocess.run(
            [*command, prompt],
            cwd=workspace,
            env=os.environ.copy(),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=int(plan["host"]["timeout_seconds"]),
            check=False,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        return_code = completed.returncode
    except subprocess.TimeoutExpired as error:
        stdout = str(error.stdout or "")
        stderr = str(error.stderr or "")
        return_code = 124
        timed_out = True
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    events, invalid_jsonl = _parse_jsonl(stdout)
    items = _completed_items(events)
    final_response = _final_response(items)
    evaluated = evaluate_workspace(workspace, scenario, final_response)
    tool_metrics = _tool_metrics(items)
    if (
        scenario in PARALLEL_SCENARIOS
        and int(tool_metrics["collab_tool_calls"]) == 0
    ):
        evaluated["verified"] = False
        evaluated["manual_interventions"] += 1
    event_errors = [
        event
        for event in events
        if event.get("type") in {"error", "turn.failed"}
    ]
    policy_declines = sum(
        1
        for item in items
        if item.get("type") == "command_execution"
        and item.get("status") == "declined"
    )
    runner_failed = (
        return_code != 0
        or timed_out
        or bool(event_errors)
        or policy_declines > 0
        or int(tool_metrics["unexpected_mcp_calls"]) > 0
        or int(tool_metrics["unmarked_sidecar_invocations"]) > 0
        or not final_response
    )
    if runner_failed:
        evaluated["verified"] = False
        evaluated["manual_interventions"] += 1

    row = {
        "scenario": scenario,
        "condition": condition,
        "pair": pair,
        "phase": phase,
        "run_id": _opaque_run_id(scenario, pair, phase),
        **evaluated,
        **_usage(events),
        **tool_metrics,
        "model_cost_usd": None,
        "wall_clock_ms": elapsed_ms,
        "host_return_code": return_code,
        "host_timed_out": timed_out,
        "host_event_errors": len(event_errors),
        "host_policy_declines": policy_declines,
        "invalid_jsonl_lines": len(invalid_jsonl),
        "final_response_present": bool(final_response),
    }
    if keep_workspace is not None:
        destination = keep_workspace / row["run_id"] / condition
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(workspace, destination)
        (destination / "codex-stderr.txt").write_text(
            stderr,
            encoding="utf-8",
        )
        (destination / "codex-events.json").write_text(
            json.dumps(events, indent=2) + "\n",
            encoding="utf-8",
        )
    temporary.cleanup()
    return row


def randomized_schedule(
    plan: dict[str, Any],
    phase: str,
    pairs: int,
    scenarios: Iterable[str] = SCENARIOS,
) -> list[tuple[str, str, int]]:
    seed = int(plan["seed"]) + (0 if phase == "validation" else 1_000_000)
    randomizer = random.Random(seed)
    schedule: list[tuple[str, str, int]] = []
    for scenario in scenarios:
        for pair in range(1, pairs + 1):
            order = list(CONDITIONS)
            randomizer.shuffle(order)
            schedule.extend((scenario, condition, pair) for condition in order)
    return schedule


def aggregate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    aggregates: list[dict[str, Any]] = []
    for scenario in SCENARIOS:
        for condition in CONDITIONS:
            selected = [
                row
                for row in rows
                if row["scenario"] == scenario
                and row["condition"] == condition
            ]
            if not selected:
                continue
            aggregates.append(
                {
                    "scenario": scenario,
                    "condition": condition,
                    "runs": len(selected),
                    "verified_runs": sum(
                        int(bool(row["verified"])) for row in selected
                    ),
                    "external_attempts": sum(
                        int(row["external_attempts"]) for row in selected
                    ),
                    "duplicate_mutations": sum(
                        int(row["duplicate_mutations"]) for row in selected
                    ),
                    "conflicting_actions": sum(
                        int(row["conflicting_actions"]) for row in selected
                    ),
                    "provider_rejections": sum(
                        int(row["provider_rejections"]) for row in selected
                    ),
                    "unresolved_ambiguous": sum(
                        int(row["unresolved_ambiguous"]) for row in selected
                    ),
                    "manual_interventions": sum(
                        int(row["manual_interventions"]) for row in selected
                    ),
                    "sidecar_calls": sum(
                        int(row["sidecar_calls"]) for row in selected
                    ),
                    "agent_tool_calls": sum(
                        int(row["agent_tool_calls"]) for row in selected
                    ),
                    "collab_tool_calls": sum(
                        int(row["collab_tool_calls"]) for row in selected
                    ),
                    "model_input_tokens": sum(
                        int(row["model_input_tokens"]) for row in selected
                    ),
                    "model_cached_input_tokens": sum(
                        int(row["model_cached_input_tokens"])
                        for row in selected
                    ),
                    "model_output_tokens": sum(
                        int(row["model_output_tokens"]) for row in selected
                    ),
                    "model_reasoning_output_tokens": sum(
                        int(row["model_reasoning_output_tokens"])
                        for row in selected
                    ),
                    "model_cost_usd": None,
                    "wall_clock_ms_total": round(
                        sum(float(row["wall_clock_ms"]) for row in selected),
                        3,
                    ),
                }
            )
    return aggregates


def _harm(row: dict[str, Any]) -> int:
    return sum(
        int(row[field])
        for field in (
            "duplicate_mutations",
            "conflicting_actions",
            "provider_rejections",
            "unresolved_ambiguous",
        )
    )


def paired_distributions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for scenario in SCENARIOS:
        pair_numbers = sorted(
            {
                int(row["pair"])
                for row in rows
                if row["scenario"] == scenario
            }
        )
        for pair in pair_numbers:
            selected = {
                str(row["condition"]): row
                for row in rows
                if row["scenario"] == scenario and int(row["pair"]) == pair
            }
            if set(selected) != set(CONDITIONS):
                continue
            without = selected["without-sidecar"]
            with_sidecar = selected["with-sidecar"]
            without_input = int(without["model_input_tokens"])
            without_latency = float(without["wall_clock_ms"])
            output.append(
                {
                    "scenario": scenario,
                    "pair": pair,
                    "verified_delta": int(bool(with_sidecar["verified"]))
                    - int(bool(without["verified"])),
                    "harm_delta": _harm(with_sidecar) - _harm(without),
                    "input_token_delta": int(
                        with_sidecar["model_input_tokens"]
                    )
                    - without_input,
                    "input_token_delta_percent": (
                        round(
                            (
                                (
                                    int(with_sidecar["model_input_tokens"])
                                    - without_input
                                )
                                / without_input
                            )
                            * 100,
                            3,
                        )
                        if without_input
                        else None
                    ),
                    "cached_input_token_delta": int(
                        with_sidecar["model_cached_input_tokens"]
                    )
                    - int(without["model_cached_input_tokens"]),
                    "output_token_delta": int(
                        with_sidecar["model_output_tokens"]
                    )
                    - int(without["model_output_tokens"]),
                    "reasoning_token_delta": int(
                        with_sidecar["model_reasoning_output_tokens"]
                    )
                    - int(without["model_reasoning_output_tokens"]),
                    "wall_clock_delta_ms": round(
                        float(with_sidecar["wall_clock_ms"])
                        - without_latency,
                        3,
                    ),
                    "wall_clock_delta_percent": (
                        round(
                            (
                                (
                                    float(with_sidecar["wall_clock_ms"])
                                    - without_latency
                                )
                                / without_latency
                            )
                            * 100,
                            3,
                        )
                        if without_latency
                        else None
                    ),
                    "sidecar_calls": int(with_sidecar["sidecar_calls"]),
                }
            )
    return output


def evaluate(
    rows: list[dict[str, Any]],
    plan: dict[str, Any],
    phase: str,
) -> dict[str, Any]:
    expected_pairs = int(
        plan[
            "validation_pairs_per_scenario"
            if phase == "validation"
            else "published_pairs_per_scenario"
        ]
    )
    distributions = paired_distributions(rows)
    complete = all(
        sum(1 for row in rows if row["scenario"] == scenario)
        == expected_pairs * len(CONDITIONS)
        for scenario in SCENARIOS
    )
    failure_rows = [
        row
        for row in rows
        if row["scenario"] in SIDE_EFFECTING_SCENARIOS
    ]
    unguarded = [
        row
        for row in failure_rows
        if row["condition"] == "without-sidecar"
    ]
    guarded = [
        row
        for row in failure_rows
        if row["condition"] == "with-sidecar"
    ]
    unguarded_harm = sum(_harm(row) for row in unguarded)
    guarded_harm = sum(_harm(row) for row in guarded)
    harm_reduction = (
        round(
            ((unguarded_harm - guarded_harm) / unguarded_harm) * 100,
            3,
        )
        if unguarded_harm
        else None
    )
    unguarded_verified_rate = (
        sum(int(bool(row["verified"])) for row in unguarded)
        / len(unguarded)
        * 100
        if unguarded
        else 0.0
    )
    guarded_verified_rate = (
        sum(int(bool(row["verified"])) for row in guarded)
        / len(guarded)
        * 100
        if guarded
        else 0.0
    )
    low_risk = [
        row
        for row in distributions
        if row["scenario"] == "low-risk-abstention"
    ]
    token_overhead_values = [
        float(row["input_token_delta_percent"])
        for row in low_risk
        if row["input_token_delta_percent"] is not None
    ]
    latency_overhead_values = [
        float(row["wall_clock_delta_percent"])
        for row in low_risk
        if row["wall_clock_delta_percent"] is not None
    ]
    median_token_overhead = (
        round(statistics.median(token_overhead_values), 3)
        if token_overhead_values
        else None
    )
    median_latency_overhead = (
        round(statistics.median(latency_overhead_values), 3)
        if latency_overhead_values
        else None
    )
    low_risk_sidecar_calls = sum(
        int(row["sidecar_calls"]) for row in low_risk
    )
    thresholds = plan["success_thresholds"]
    checks = {
        "failure_scenario_harm_reduction": (
            harm_reduction is not None
            and harm_reduction
            >= float(
                thresholds["failure_scenario_harm_reduction_percent"]
            )
        ),
        "verified_completion": (
            unguarded_verified_rate - guarded_verified_rate
            <= float(
                thresholds[
                    "maximum_verified_completion_drop_percentage_points"
                ]
            )
        ),
        "low_risk_input_token_overhead": (
            median_token_overhead is not None
            and median_token_overhead
            <= float(
                thresholds[
                    "maximum_low_risk_input_token_overhead_percent"
                ]
            )
        ),
        "low_risk_latency_overhead": (
            median_latency_overhead is not None
            and median_latency_overhead
            <= float(
                thresholds["maximum_low_risk_latency_overhead_percent"]
            )
        ),
        "low_risk_abstention": (
            low_risk_sidecar_calls
            == int(thresholds["low_risk_sidecar_calls"])
        ),
    }
    return {
        "status": (
            "incomplete"
            if not complete
            else "passed"
            if all(checks.values())
            else "failed"
        ),
        "complete": complete,
        "expected_pairs_per_scenario": expected_pairs,
        "checks": checks,
        "observed": {
            "unguarded_harmful_events": unguarded_harm,
            "guarded_harmful_events": guarded_harm,
            "harm_reduction_percent": harm_reduction,
            "unguarded_verified_rate_percent": round(
                unguarded_verified_rate,
                3,
            ),
            "guarded_verified_rate_percent": round(
                guarded_verified_rate,
                3,
            ),
            "verified_completion_drop_percentage_points": round(
                unguarded_verified_rate - guarded_verified_rate,
                3,
            ),
            "low_risk_median_input_token_overhead_percent": (
                median_token_overhead
            ),
            "low_risk_median_latency_overhead_percent": (
                median_latency_overhead
            ),
            "low_risk_sidecar_calls": low_risk_sidecar_calls,
        },
    }


def build_report(
    plan: dict[str, Any],
    phase: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "evidence_class": "metered-agent-host",
        "phase": phase,
        "plan_sha256": hashlib.sha256(
            (HERE / "preregistered-plan.json").read_bytes()
        ).hexdigest(),
        "protocol_sha256": protocol_sha256(),
        "controls": plan["host"],
        "cost_note": (
            "ChatGPT-managed Codex auth reports tokens but no per-run dollar "
            "rate; model_cost_usd remains null."
        ),
        "rows": rows,
        "aggregates": aggregate(rows),
        "paired_distributions": paired_distributions(rows),
        "evaluation": evaluate(rows, plan, phase),
    }
