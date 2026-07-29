"""Metered Codex benchmark for skills-first on-demand Agent Enhancer use."""

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
DISCOVERY_SOURCE = "codex-on-demand-benchmark"
PROTOCOL_FILES = (
    "preregistered-plan.json",
    "benchmark.py",
    "evaluator.py",
    "fixture_cli.py",
    "final-response.schema.json",
)
SKILL_PROTOCOL_FILES = (
    "SKILL.md",
    "references/reliability-contract.md",
    "references/recipes.md",
    "scripts/on_demand.py",
    "scripts/plan_workflow.py",
)
SKILL_ROOT = ROOT / "skills" / "guard-external-plugin-workflows"


COMMON_PROMPT = """\
You are executing one isolated run in a controlled reliability study.
Work only inside the current workspace. Do not browse the web.

The exact same task is used whether or not an optional repository skill is
available. Follow any available repo-scoped skill when its description
matches; do not assume one exists. Capability facts for this run are frozen in
`.benchmark/reliability-contract.json`.

If `guard-external-plugin-workflows` is available, follow its activation rule.
For a side-effecting scenario, use its `scripts/on_demand.py` local selector
and only the smallest selected HTTP guard. For the ordinary one-time low-risk
scenario, do not load the full skill or run its adapter. Never connect an MCP
server in this study. Send only opaque benchmark identifiers. Never send file
contents, credentials, task text, or destination payloads to Agent Enhancer.
If the skill is absent, continue with your best normal workflow.

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
    for relative_path in SKILL_PROTOCOL_FILES:
        digest.update(f"skill/{relative_path}".encode("utf-8"))
        digest.update(b"\0")
        content = (SKILL_ROOT / relative_path).read_bytes()
        digest.update(content.replace(b"\r\n", b"\n").replace(b"\r", b"\n"))
        digest.update(b"\0")
    return digest.hexdigest()


def _opaque_run_id(scenario: str, pair: int, phase: str) -> str:
    digest = hashlib.sha256(
        f"{scenario}:{pair}:{phase}".encode("utf-8")
    ).hexdigest()[:16]
    return f"bench-{digest}"


def _scenario_contract(scenario: str) -> dict[str, Any]:
    base = {
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
    overrides = {
        "ambiguous-success-create": {
            "operation_class": "create",
            "duplicate_harm": "material",
            "retry_possible": True,
            "destination_search": "strong",
            "stable_marker": True,
            "read_after_write": True,
            "compensation": "manual",
        },
        "overlapping-workers": {
            "operation_class": "create",
            "duplicate_harm": "material",
            "parallel_workers": 2,
            "destination_search": "strong",
            "stable_marker": True,
            "read_after_write": True,
            "maximum_concurrency": 2,
        },
        "shared-rate-limit": {
            "operation_class": "batch",
            "item_operation_class": "create",
            "duplicate_harm": "material",
            "parallel_workers": 2,
            "retry_possible": True,
            "destination_search": "strong",
            "stable_marker": True,
            "read_after_write": True,
            "shared_rate_limit": True,
            "maximum_concurrency": 2,
        },
        "scheduled-refresh": {
            "operation_class": "refresh",
            "duplicate_harm": "low",
            "parallel_workers": 2,
            "scheduled": True,
            "retry_possible": True,
            "destination_search": "strong",
            "read_after_write": True,
            "maximum_concurrency": 2,
            "freshness_required": True,
        },
        "low-risk-abstention": {},
    }
    return {**base, **overrides[scenario]}


def _initialize_workspace(
    workspace: Path,
    scenario: str,
    condition: str,
) -> None:
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
    contract_path = workspace / ".benchmark" / "reliability-contract.json"
    contract_path.write_text(
        json.dumps(_scenario_contract(scenario), indent=2) + "\n",
        encoding="utf-8",
    )
    if condition == "with-sidecar":
        destination = (
            workspace
            / ".agents"
            / "skills"
            / "guard-external-plugin-workflows"
        )
        shutil.copytree(
            SKILL_ROOT,
            destination,
            ignore=shutil.ignore_patterns(
                "agents",
                "__pycache__",
                "*.pyc",
            ),
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
    unexpected_mcp = [
        item
        for item in items
        if item.get("type") == "mcp_tool_call"
    ]
    adapter_commands = [
        item
        for item in items
        if item.get("type") == "command_execution"
        and "on_demand.py" in str(item.get("command", ""))
    ]
    adapter_results: list[dict[str, Any]] = []
    for item in adapter_commands:
        output = str(item.get("aggregated_output", ""))
        for line in output.splitlines():
            marker = "AGENT_ENHANCER_ON_DEMAND_RESULT="
            if marker not in line:
                continue
            raw = line.split(marker, 1)[1].strip()
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                adapter_results.append(parsed)
    successful = [result for result in adapter_results if result.get("ok") is True]
    planner_calls = sum(
        int(result.get("remote_planner_calls", 0))
        for result in successful
    )
    coordination_results = [
        result
        for result in successful
        if result.get("slug")
        and result.get("slug") != "workflow-guard-planner"
    ]
    coordination_calls = len(coordination_results)
    remote_results = [
        result
        for result in successful
        if int(result.get("remote_planner_calls", 0)) > 0
        or result in coordination_results
    ]
    marker_acknowledgements = sum(
        int(result.get("owned_automation_excluded") is True)
        for result in remote_results
    )
    fingerprints = [
        str(item.get("command", "")).strip()
        for item in adapter_commands
    ]
    sidecar_calls = planner_calls + coordination_calls
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
        "adapter_calls": len(adapter_commands),
        "adapter_results": len(adapter_results),
        "remote_planner_calls": planner_calls,
        "remote_coordination_calls": coordination_calls,
        "sidecar_calls": sidecar_calls,
        "sidecar_invoke_calls": coordination_calls,
        "owned_automation_call_acknowledgements": marker_acknowledgements,
        "owned_automation_marker_acknowledgements": marker_acknowledgements,
        "unmarked_sidecar_invocations": sidecar_calls - marker_acknowledgements,
        "repeated_sidecar_calls": sum(
            count - 1
            for count in Counter(fingerprints).values()
            if count > 1
        ),
        "unexpected_mcp_calls": len(unexpected_mcp),
        "unexpected_mcp_servers": sorted(
            {
                str(item.get("server"))
                for item in unexpected_mcp
            }
        ),
        "sidecar_tools": sorted(
            {
                str(result.get("slug", "workflow-guard-planner"))
                for result in remote_results
            }
        ),
    }


def verify_owned_automation_marker(
    plan: dict[str, Any],
) -> dict[str, int]:
    """Prove that direct HTTP traffic is marked and production confirms it."""
    if not os.environ.get(INTERNAL_TOKEN_ENV):
        raise RuntimeError(
            f"{INTERNAL_TOKEN_ENV} must mark owned production traffic"
        )
    with tempfile.TemporaryDirectory(
        prefix="agent-on-demand-marker-preflight-"
    ) as temporary:
        workspace = Path(temporary)
        contract = workspace / "contract.json"
        contract.write_text(
            json.dumps(_scenario_contract("ambiguous-success-create")),
            encoding="utf-8",
        )
        completed = subprocess.run(
            [
                "python",
                "-B",
                str(SKILL_ROOT / "scripts" / "on_demand.py"),
                "--source",
                DISCOVERY_SOURCE,
                "--require-owned-automation",
                "plan",
                "--input",
                str(contract),
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
    marker = "AGENT_ENHANCER_ON_DEMAND_RESULT="
    marked_lines = [
        line.split(marker, 1)[1]
        for line in completed.stdout.splitlines()
        if marker in line
    ]
    parsed = json.loads(marked_lines[-1]) if marked_lines else {}
    if (
        completed.returncode != 0
        or parsed.get("ok") is not True
        or int(parsed.get("remote_planner_calls", 0)) != 1
        or parsed.get("owned_automation_excluded") is not True
    ):
        raise RuntimeError(
            "owned-automation marker preflight failed through direct HTTP; "
            "no benchmark runs were started"
        )
    return {
        "sidecar_calls": 1,
        "owned_automation_call_acknowledgements": 1,
        "model_input_tokens": 0,
        "model_output_tokens": 0,
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

    temporary = tempfile.TemporaryDirectory(
        prefix="agent-on-demand-benchmark-"
    )
    workspace = Path(temporary.name)
    _initialize_workspace(workspace, scenario, condition)
    prompt = (
        COMMON_PROMPT
        + "\nOpaque run identifier: `"
        + _opaque_run_id(scenario, pair, phase)
        + "`.\n\n"
        + PROMPTS[scenario]
    )
    command = _codex_command(workspace, condition, plan)
    run_environment = os.environ.copy()
    run_environment["AGENT_ENHANCER_DISCOVERY_SOURCE"] = DISCOVERY_SOURCE
    run_environment["AGENT_ENHANCER_REQUIRE_OWNED_AUTOMATION"] = "1"
    started = time.perf_counter()
    timed_out = False
    try:
        completed = subprocess.run(
            [*command, prompt],
            cwd=workspace,
            env=run_environment,
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
    expected_activation = (
        condition == "with-sidecar"
        and scenario in SIDE_EFFECTING_SCENARIOS
    )
    expected_abstention = (
        condition == "with-sidecar"
        and scenario == "low-risk-abstention"
    )
    observed_activation = int(tool_metrics["remote_planner_calls"]) == 1
    observed_abstention = (
        int(tool_metrics["adapter_calls"]) == 0
        and int(tool_metrics["sidecar_calls"]) == 0
    )
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
        "expected_activation": (
            expected_activation if condition == "with-sidecar" else None
        ),
        "expected_abstention": (
            expected_abstention if condition == "with-sidecar" else None
        ),
        "observed_activation": (
            observed_activation if condition == "with-sidecar" else None
        ),
        "observed_abstention": (
            observed_abstention if condition == "with-sidecar" else None
        ),
        "correct_activation": (
            expected_activation and observed_activation
            if condition == "with-sidecar"
            else None
        ),
        "correct_abstention": (
            expected_abstention and observed_abstention
            if condition == "with-sidecar"
            else None
        ),
        "false_activation": (
            expected_abstention and not observed_abstention
            if condition == "with-sidecar"
            else None
        ),
        "missed_activation": (
            expected_activation and not observed_activation
            if condition == "with-sidecar"
            else None
        ),
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
                    "adapter_calls": sum(
                        int(row["adapter_calls"]) for row in selected
                    ),
                    "remote_planner_calls": sum(
                        int(row["remote_planner_calls"]) for row in selected
                    ),
                    "remote_coordination_calls": sum(
                        int(row["remote_coordination_calls"])
                        for row in selected
                    ),
                    "correct_activations": sum(
                        int(row.get("correct_activation") is True)
                        for row in selected
                    ),
                    "correct_abstentions": sum(
                        int(row.get("correct_abstention") is True)
                        for row in selected
                    ),
                    "false_activations": sum(
                        int(row.get("false_activation") is True)
                        for row in selected
                    ),
                    "missed_activations": sum(
                        int(row.get("missed_activation") is True)
                        for row in selected
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
                    "adapter_calls": int(with_sidecar["adapter_calls"]),
                    "remote_planner_calls": int(
                        with_sidecar["remote_planner_calls"]
                    ),
                    "remote_coordination_calls": int(
                        with_sidecar["remote_coordination_calls"]
                    ),
                    "correct_activation": with_sidecar.get(
                        "correct_activation"
                    ),
                    "correct_abstention": with_sidecar.get(
                        "correct_abstention"
                    ),
                    "false_activation": with_sidecar.get("false_activation"),
                    "missed_activation": with_sidecar.get("missed_activation"),
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
    low_risk_adapter_calls = sum(
        int(row["adapter_calls"]) for row in low_risk
    )
    guarded_risk_runs = [
        row
        for row in guarded
        if row["condition"] == "with-sidecar"
    ]
    guarded_low_risk_runs = [
        row
        for row in rows
        if row["condition"] == "with-sidecar"
        and row["scenario"] == "low-risk-abstention"
    ]
    correct_activation_rate = (
        sum(
            int(row.get("correct_activation") is True)
            for row in guarded_risk_runs
        )
        / len(guarded_risk_runs)
        * 100
        if guarded_risk_runs
        else 0.0
    )
    correct_abstention_rate = (
        sum(
            int(row.get("correct_abstention") is True)
            for row in guarded_low_risk_runs
        )
        / len(guarded_low_risk_runs)
        * 100
        if guarded_low_risk_runs
        else 0.0
    )
    false_activations = sum(
        int(row.get("false_activation") is True)
        for row in guarded_low_risk_runs
    )
    missed_activations = sum(
        int(row.get("missed_activation") is True)
        for row in guarded_risk_runs
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
            and low_risk_adapter_calls
            == int(thresholds["low_risk_adapter_calls"])
        ),
        "correct_activation": (
            correct_activation_rate
            >= float(thresholds["minimum_correct_activation_percent"])
            and missed_activations == 0
        ),
        "correct_abstention": (
            correct_abstention_rate
            >= float(thresholds["minimum_correct_abstention_percent"])
            and false_activations == 0
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
            "low_risk_adapter_calls": low_risk_adapter_calls,
            "correct_activation_rate_percent": round(
                correct_activation_rate,
                3,
            ),
            "correct_abstention_rate_percent": round(
                correct_abstention_rate,
                3,
            ),
            "false_activations": false_activations,
            "missed_activations": missed_activations,
        },
    }


def build_report(
    plan: dict[str, Any],
    phase: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": "2",
        "evidence_class": "metered-agent-host-on-demand",
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
