#!/usr/bin/env python3
"""Skills-first, on-demand adapter for the public Agent Enhancer HTTP API."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Protocol
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://liberated.site/v1/tools"
DEFAULT_SOURCE = "skills-on-demand"
RESULT_MARKER = "AGENT_ENHANCER_ON_DEMAND_RESULT="
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
HEX_DIGEST_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")
HMAC_DIGEST_PATTERN = re.compile(r"^hmac-sha256:[a-f0-9]{64}$")
UUID_PATTERN = re.compile(
    r"(?:^|[:_-])[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-"
    r"[1-5a-fA-F0-9][a-fA-F0-9]{3}-[89abABa-fA-F0-9]"
    r"[a-fA-F0-9]{3}-[a-fA-F0-9]{12}$"
)
PREFIXED_OPAQUE_PATTERN = re.compile(
    r"^[A-Za-z0-9_-]{1,32}[:_-][A-Za-z0-9_-]{16,127}$"
)
CONTROL_TOKEN_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
FAILURE_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
LOCAL_LABEL_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")

ALLOWED_TOOLS = frozenset(
    {
        "workflow-guard-planner",
        "workflow-checkpoint",
        "penny-lock",
        "global-seen-stamp",
        "exactly-once-baton",
        "negative-cache-ticket",
        "swarm-semaphore",
        "swarm-rate-gate",
        "barrier-bell",
        "freshness-lease",
    }
)
TOOL_FIELDS = {
    "workflow-guard-planner": frozenset(
        {
            "compensation",
            "conditional_write",
            "contract_version",
            "delivery_status",
            "destination_search",
            "duplicate_harm",
            "freshness_required",
            "item_operation_class",
            "maximum_concurrency",
            "operation_class",
            "parallel_workers",
            "provider_idempotency",
            "read_after_write",
            "retry_possible",
            "scheduled",
            "shared_rate_limit",
            "stable_marker",
        }
    ),
    "workflow-checkpoint": frozenset(
        {
            "action",
            "claim_ttl_seconds",
            "evidence_fingerprint",
            "evidence_type",
            "expected_generation",
            "from_stage",
            "holder",
            "namespace",
            "observation_key",
            "retry_failed",
            "state_ttl_seconds",
            "to_stage",
            "workflow_key",
        }
    ),
    "penny-lock": frozenset({"key", "namespace", "owner", "ttl_seconds"}),
    "global-seen-stamp": frozenset(
        {"content_sha256", "namespace", "ttl_seconds"}
    ),
    "exactly-once-baton": frozenset(
        {"baton", "namespace", "operation", "ttl_seconds"}
    ),
    "negative-cache-ticket": frozenset(
        {"failure_code", "key", "namespace", "operation", "ttl_seconds"}
    ),
    "swarm-semaphore": frozenset(
        {"action", "capacity", "holder", "key", "namespace", "ttl_seconds"}
    ),
    "swarm-rate-gate": frozenset(
        {
            "action",
            "capacity",
            "key",
            "namespace",
            "operation_key",
            "refill_interval_seconds",
            "refill_tokens",
            "requested_tokens",
            "ttl_seconds",
        }
    ),
    "barrier-bell": frozenset(
        {"action", "key", "namespace", "participant", "threshold", "ttl_seconds"}
    ),
    "freshness-lease": frozenset(
        {"action", "holder", "key", "namespace", "ttl_seconds"}
    ),
}
IDENTITY_FIELDS = frozenset(
    {
        "baton",
        "content_sha256",
        "evidence_fingerprint",
        "holder",
        "key",
        "namespace",
        "observation_key",
        "operation_key",
        "owner",
        "participant",
        "workflow_key",
    }
)
CONTROL_STRING_FIELDS = frozenset(
    {
        "action",
        "compensation",
        "contract_version",
        "destination_search",
        "duplicate_harm",
        "evidence_type",
        "failure_code",
        "from_stage",
        "item_operation_class",
        "operation",
        "operation_class",
        "provider_idempotency",
        "to_stage",
    }
)
FORBIDDEN_FIELD_PARTS = frozenset(
    {
        "address",
        "api_key",
        "authorization",
        "conversation",
        "cookie",
        "credential",
        "customer",
        "document",
        "email",
        "message",
        "password",
        "payload",
        "phone",
        "private_key",
        "record",
        "secret",
        "task_text",
        "token",
        "url",
    }
)
PLAN_FIELDS = (
    "valid",
    "decision",
    "decision_reason",
    "profile",
    "additional_profiles",
    "guarantee",
    "stages",
    "timeout_recovery",
    "residual_risks",
    "unsupported_claims",
)


def _load_local_planner():
    path = Path(__file__).with_name("plan_workflow.py")
    spec = importlib.util.spec_from_file_location(
        "agent_enhancer_local_workflow_planner",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load the local workflow planner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LOCAL_PLANNER = _load_local_planner()


class OnDemandError(ValueError):
    """Typed local validation, transport, or planner-drift failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ToolClient(Protocol):
    calls: int

    def invoke(
        self,
        slug: str,
        tool_input: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Invoke one allowed hosted tool and return a transport record."""


def _is_opaque(value: str) -> bool:
    return bool(
        HEX_DIGEST_PATTERN.fullmatch(value)
        or UUID_PATTERN.search(value)
        or PREFIXED_OPAQUE_PATTERN.fullmatch(value)
    )


def _validate_control_string(field: str, value: str) -> None:
    if field == "contract_version":
        valid = value == "1"
    elif field == "failure_code":
        valid = FAILURE_CODE_PATTERN.fullmatch(value)
    else:
        valid = CONTROL_TOKEN_PATTERN.fullmatch(value)
    if not valid:
        raise OnDemandError(
            "UNSAFE_INPUT",
            f"{field} must be a bounded control token, not free text",
        )


def _validate_safe_value(
    value: Any,
    *,
    field: str | None = None,
    depth: int = 0,
) -> None:
    if depth > 6:
        raise OnDemandError("UNSAFE_INPUT", "input nesting exceeds six levels")
    if isinstance(value, dict):
        for raw_key, child in value.items():
            if not isinstance(raw_key, str):
                raise OnDemandError("UNSAFE_INPUT", "all field names must be strings")
            normalized = raw_key.lower()
            if any(part in normalized for part in FORBIDDEN_FIELD_PARTS):
                raise OnDemandError(
                    "UNSAFE_INPUT",
                    f"field {raw_key!r} may contain private or destination data",
                )
            _validate_safe_value(child, field=normalized, depth=depth + 1)
        return
    if isinstance(value, list):
        if len(value) > 32:
            raise OnDemandError("UNSAFE_INPUT", "arrays may contain at most 32 items")
        for child in value:
            _validate_safe_value(child, field=field, depth=depth + 1)
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    if not isinstance(value, str):
        raise OnDemandError("UNSAFE_INPUT", "input contains an unsupported value")
    if field in IDENTITY_FIELDS:
        if field == "evidence_fingerprint":
            valid = HMAC_DIGEST_PATTERN.fullmatch(value)
        elif field == "content_sha256":
            valid = HEX_DIGEST_PATTERN.fullmatch(value)
        else:
            valid = _is_opaque(value)
        if not valid:
            raise OnDemandError(
                "RAW_IDENTIFIER_REJECTED",
                f"{field} must be an opaque digest, UUID-scoped value, or token",
            )
        return
    if field in CONTROL_STRING_FIELDS:
        _validate_control_string(field, value)
        return
    raise OnDemandError(
        "UNSAFE_INPUT",
        f"free-text field {field!r} is not allowed by the on-demand adapter",
    )


def validate_tool_request(
    slug: str,
    tool_input: Any,
    idempotency_key: str | None,
) -> dict[str, Any]:
    """Validate the local privacy and transport boundary before any network call."""

    if slug not in ALLOWED_TOOLS:
        raise OnDemandError(
            "TOOL_NOT_ALLOWED",
            f"{slug!r} is not in the on-demand reliability allowlist",
        )
    if not isinstance(tool_input, dict):
        raise OnDemandError("INVALID_INPUT", "tool input must be one JSON object")
    encoded = json.dumps(tool_input, separators=(",", ":"), ensure_ascii=True)
    if len(encoded.encode("utf-8")) > 16_384:
        raise OnDemandError("UNSAFE_INPUT", "tool input exceeds 16 KiB")
    _validate_safe_value(tool_input)
    unknown_fields = set(tool_input) - TOOL_FIELDS[slug]
    if unknown_fields:
        raise OnDemandError(
            "INVALID_INPUT",
            f"{slug} input contains unknown fields: {sorted(unknown_fields)}",
        )
    if slug == "workflow-guard-planner":
        try:
            LOCAL_PLANNER.validate_contract(tool_input)
        except LOCAL_PLANNER.PlannerError as error:
            raise OnDemandError(error.code, error.message) from error
    if idempotency_key is not None and not IDEMPOTENCY_PATTERN.fullmatch(
        idempotency_key
    ):
        raise OnDemandError(
            "INVALID_IDEMPOTENCY_KEY",
            "idempotency_key must be 16-128 letters, numbers, underscores, or hyphens",
        )
    if slug != "workflow-guard-planner" and idempotency_key is None:
        action = tool_input.get("action") or tool_input.get("operation")
        if not (
            slug == "workflow-checkpoint" and action == "status"
        ):
            raise OnDemandError(
                "IDEMPOTENCY_KEY_REQUIRED",
                "stateful on-demand calls require a stable idempotency_key",
            )
    return tool_input


class DirectToolClient:
    """No-auth standard-library client for the existing generated HTTP API."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        source: str = DEFAULT_SOURCE,
        timeout_seconds: float = 20.0,
        require_owned_automation: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.source = source
        self.timeout_seconds = timeout_seconds
        self.require_owned_automation = require_owned_automation
        self.calls = 0

    def invoke(
        self,
        slug: str,
        tool_input: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        validate_tool_request(slug, tool_input, idempotency_key)
        marker = os.environ.get("AGENT_ENHANCER_INTERNAL_METRICS_TOKEN")
        if self.require_owned_automation and not marker:
            raise OnDemandError(
                "OWNED_AUTOMATION_MARKER_REQUIRED",
                "set AGENT_ENHANCER_INTERNAL_METRICS_TOKEN before benchmark traffic",
            )
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "agent-enhancer-skills-on-demand/1.7.1",
            "X-Agent-Discovery-Source": self.source,
        }
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        if marker:
            headers["X-Agent-Internal-Metrics"] = marker
        url = (
            f"{self.base_url}/{quote(slug, safe='')}"
            f"?source={quote(self.source, safe='')}"
        )
        request = Request(
            url,
            data=json.dumps(
                tool_input,
                separators=(",", ":"),
            ).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        self.calls += 1
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
                owned_excluded = (
                    response.headers.get(
                        "X-Agent-Owned-Automation-Excluded",
                        "",
                    ).lower()
                    == "true"
                )
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise OnDemandError(
                "HTTP_ERROR",
                f"{slug} returned HTTP {error.code}: {detail}",
            ) from error
        except URLError as error:
            raise OnDemandError(
                "CONNECTION_FAILED",
                f"{slug} connection failed: {error.reason}",
            ) from error
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise OnDemandError(
                "INVALID_RESPONSE",
                f"{slug} returned invalid JSON",
            ) from error
        if not isinstance(body, dict):
            raise OnDemandError("INVALID_RESPONSE", "response was not a JSON object")
        result = body.get("result")
        if body.get("ok") is not True or not isinstance(result, dict):
            error = body.get("error")
            code = error.get("code") if isinstance(error, dict) else "TOOL_ERROR"
            message = (
                error.get("message")
                if isinstance(error, dict)
                else "tool response was not successful"
            )
            raise OnDemandError(str(code), str(message))
        if self.require_owned_automation and not owned_excluded:
            raise OnDemandError(
                "OWNED_AUTOMATION_NOT_CONFIRMED",
                "production did not confirm exclusion from public metrics",
            )
        return {
            "slug": slug,
            "result": result,
            "request_id": body.get("meta", {}).get("request_id"),
            "owned_automation_excluded": owned_excluded,
            "remote_calls": self.calls,
        }


def _digest_token(prefix: str, *values: str) -> str:
    digest = hashlib.sha256()
    digest.update(prefix.encode("utf-8"))
    for value in values:
        digest.update(b"\0")
        digest.update(value.encode("utf-8"))
    return f"{prefix}_{digest.hexdigest()}"


def _checkpoint_step(
    *,
    name: str,
    namespace: str,
    workflow_key: str,
    holder: str,
    from_stage: str,
    to_stage: str,
    evidence_type: str | None = None,
) -> dict[str, Any]:
    return {
        "input": {
            "action": "transition",
            "namespace": namespace,
            "workflow_key": workflow_key,
            "holder": holder,
            "expected_generation": 1,
            "from_stage": from_stage,
            "to_stage": to_stage,
            "observation_key": _digest_token(
                "observation",
                namespace,
                workflow_key,
                holder,
                name,
            ),
            "evidence_type": evidence_type,
            "evidence_fingerprint": None,
        },
        "idempotency_key": _digest_token(
            "checkpoint",
            namespace,
            workflow_key,
            holder,
            name,
        ),
    }


def build_checkpoint_blueprint(
    *,
    scope: str,
    operation_id: str,
    holder_labels: list[str],
    namespace_uuid: str | None = None,
    claim_ttl_seconds: int = 120,
    state_ttl_seconds: int = 3_600,
) -> dict[str, Any]:
    """Build a local-only, executable first-generation checkpoint flow."""

    if not CONTROL_TOKEN_PATTERN.fullmatch(scope) or len(scope) > 32:
        raise OnDemandError(
            "INVALID_BLUEPRINT",
            "scope must be a 1-32 character lowercase control token",
        )
    if not _is_opaque(operation_id):
        raise OnDemandError(
            "INVALID_BLUEPRINT",
            "operation_id must already be an opaque digest, UUID, or scoped token",
        )
    if not holder_labels or len(holder_labels) > 32:
        raise OnDemandError(
            "INVALID_BLUEPRINT",
            "provide between one and 32 local holder labels",
        )
    if len(set(holder_labels)) != len(holder_labels):
        raise OnDemandError("INVALID_BLUEPRINT", "holder labels must be unique")
    if any(not LOCAL_LABEL_PATTERN.fullmatch(label) for label in holder_labels):
        raise OnDemandError(
            "INVALID_BLUEPRINT",
            "holder labels must use 1-64 letters, numbers, dot, colon, underscore, or hyphen",
        )
    if not 60 <= claim_ttl_seconds <= 3_600:
        raise OnDemandError(
            "INVALID_BLUEPRINT",
            "claim_ttl_seconds must be between 60 and 3600",
        )
    if not claim_ttl_seconds <= state_ttl_seconds <= 3_600:
        raise OnDemandError(
            "INVALID_BLUEPRINT",
            "state_ttl_seconds must be between claim_ttl_seconds and 3600",
        )
    try:
        parsed_uuid = (
            uuid.uuid4()
            if namespace_uuid is None
            else uuid.UUID(namespace_uuid)
        )
    except ValueError as error:
        raise OnDemandError(
            "INVALID_BLUEPRINT",
            "namespace_uuid must be a canonical UUID v4",
        ) from error
    if parsed_uuid.version != 4 or (
        namespace_uuid is not None and namespace_uuid != str(parsed_uuid)
    ):
        raise OnDemandError(
            "INVALID_BLUEPRINT",
            "namespace_uuid must be a canonical UUID v4",
        )

    namespace = f"{scope}:{parsed_uuid}"
    workflow_key = _digest_token("workflow", operation_id)
    holders: dict[str, str] = {}
    for label in holder_labels:
        holders[label] = _digest_token("holder", operation_id, label)
    return {
        "schema_version": "1",
        "fresh_namespace_only": True,
        "namespace": namespace,
        "workflow_key": workflow_key,
        "generation": 1,
        "claim_ttl_seconds": claim_ttl_seconds,
        "state_ttl_seconds": state_ttl_seconds,
        "holders": holders,
        "rules": [
            "Run claim concurrently for each holder and admit only acquired or reused.",
            "Run start immediately before the one external mutation.",
            "After a lost response run uncertain, reconcile, and never blind-retry.",
            "Run exactly one verify step only after destination evidence is observed.",
        ],
    }


def invoke_checkpoint_blueprint_step(
    blueprint: dict[str, Any],
    *,
    holder_label: str,
    step: str,
    client: ToolClient | None = None,
) -> dict[str, Any]:
    if blueprint.get("schema_version") != "1" or not blueprint.get(
        "fresh_namespace_only"
    ):
        raise OnDemandError("INVALID_BLUEPRINT", "unsupported checkpoint blueprint")
    namespace = blueprint.get("namespace")
    workflow_key = blueprint.get("workflow_key")
    holder = blueprint.get("holders", {}).get(holder_label)
    if step == "status":
        request = {
            "input": {
                "action": "status",
                "namespace": namespace,
                "workflow_key": workflow_key,
            },
            "idempotency_key": None,
        }
    elif step == "claim" and isinstance(holder, str):
        request = {
            "input": {
                "action": "claim",
                "namespace": namespace,
                "workflow_key": workflow_key,
                "holder": holder,
                "claim_ttl_seconds": blueprint.get("claim_ttl_seconds"),
                "state_ttl_seconds": blueprint.get("state_ttl_seconds"),
                "retry_failed": False,
            },
            "idempotency_key": _digest_token(
                "checkpoint",
                str(namespace),
                str(workflow_key),
                holder,
                "claim",
            ),
        }
    else:
        transitions = {
            "start": (
                "claimed",
                "external_attempt_started",
                None,
            ),
            "uncertain": (
                "external_attempt_started",
                "external_result_uncertain",
                None,
            ),
            "verify-after-attempt": (
                "external_attempt_started",
                "caller_verified",
                "stable_marker_readback",
            ),
            "verify-after-uncertain": (
                "external_result_uncertain",
                "caller_verified",
                "stable_marker_readback",
            ),
            "fail-before-attempt": ("claimed", "failed", None),
            "fail-after-attempt": (
                "external_attempt_started",
                "failed",
                None,
            ),
            "fail-after-uncertain": (
                "external_result_uncertain",
                "failed",
                None,
            ),
        }
        transition = transitions.get(step)
        request = (
            _checkpoint_step(
                name=step,
                namespace=str(namespace),
                workflow_key=str(workflow_key),
                holder=holder,
                from_stage=transition[0],
                to_stage=transition[1],
                evidence_type=transition[2],
            )
            if transition is not None and isinstance(holder, str)
            else None
        )
    if not isinstance(request, dict) or not isinstance(request.get("input"), dict):
        raise OnDemandError(
            "INVALID_BLUEPRINT",
            "the requested holder or checkpoint step does not exist",
        )
    result = invoke_tool(
        "workflow-checkpoint",
        request["input"],
        request.get("idempotency_key"),
        client,
    )
    return {
        **result,
        "blueprint_step": step,
        "holder_label": holder_label,
    }


def _execution_recipe(plan: dict[str, Any]) -> dict[str, Any] | None:
    if plan["decision"] == "no-sidecar":
        return None
    stages = plan["stages"]
    candidate_tools = [
        stage["candidate_tool"]
        for stage in stages
        if "candidate_tool" in stage
    ]
    required_guard = (
        "workflow-checkpoint"
        if "workflow-checkpoint" in candidate_tools
        else (candidate_tools[0] if candidate_tools else None)
    )
    actions = [stage["action"] for stage in stages]
    preflight = [
        action
        for action in actions
        if action
        in {
            "search_stable_marker",
            "read_current_version",
            "query_delivery_status",
        }
    ]
    verification = [
        action
        for action in actions
        if action
        in {
            "read_after_write",
            "query_delivery_status",
            "record_caller_verified",
        }
    ]
    uses_checkpoint = required_guard == "workflow-checkpoint"
    return {
        "required_guard": required_guard,
        "external_preflight": preflight,
        "attempt_boundary_transition": (
            "claimed_to_external_attempt_started" if uses_checkpoint else None
        ),
        "verification": verification,
        "uncertainty_recovery": plan["timeout_recovery"],
        "prohibited_action": (
            "blind_external_retry_after_uncertain_write"
            if uses_checkpoint
            else None
        ),
        "local_blueprint_command": (
            "checkpoint-blueprint" if uses_checkpoint else None
        ),
        "checkpoint_step_command": (
            "checkpoint-step" if uses_checkpoint else None
        ),
        "namespace_rule": (
            "<scope>:<fresh UUID v4>" if uses_checkpoint else None
        ),
    }


def plan_on_demand(
    contract: dict[str, Any],
    client: ToolClient | None = None,
) -> dict[str, Any]:
    """Select locally, abstain locally, or verify one hosted plan."""

    try:
        local = LOCAL_PLANNER.plan_workflow(contract)
    except LOCAL_PLANNER.PlannerError as error:
        raise OnDemandError(error.code, error.message) from error
    if local["decision"] == "no-sidecar":
        return {
            "decision": "no-sidecar",
            "activation": "local-abstention",
            "remote_planner_calls": 0,
            "remote_coordination_calls": 0,
            "plan": local,
            "execution_recipe": None,
        }
    selected_client = client or DirectToolClient()
    before = selected_client.calls
    transport = selected_client.invoke(
        "workflow-guard-planner",
        contract,
        None,
    )
    remote = transport["result"]
    for field in PLAN_FIELDS:
        if remote.get(field) != local.get(field):
            raise OnDemandError(
                "PLANNER_DRIFT",
                f"local and hosted planners disagree on {field}",
            )
    return {
        "decision": "sidecar",
        "activation": "remote-after-local-selection",
        "remote_planner_calls": selected_client.calls - before,
        "remote_coordination_calls": 0,
        "owned_automation_excluded": transport.get(
            "owned_automation_excluded",
            False,
        ),
        "plan": remote,
        "execution_recipe": _execution_recipe(remote),
    }


def invoke_tool(
    slug: str,
    tool_input: dict[str, Any],
    idempotency_key: str | None,
    client: ToolClient | None = None,
) -> dict[str, Any]:
    """Invoke one selected guard after the agent has authorized that guard."""

    selected_client = client or DirectToolClient()
    return selected_client.invoke(slug, tool_input, idempotency_key)


def _read_json(path: str) -> Any:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _emit(result: dict[str, Any]) -> None:
    print(
        RESULT_MARKER
        + json.dumps(
            result,
            separators=(",", ":"),
            sort_keys=True,
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Select and invoke Agent Enhancer guards on demand.",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("AGENT_ENHANCER_HTTP_BASE_URL", DEFAULT_BASE_URL),
    )
    parser.add_argument(
        "--source",
        default=os.environ.get("AGENT_ENHANCER_DISCOVERY_SOURCE", DEFAULT_SOURCE),
    )
    parser.add_argument(
        "--require-owned-automation",
        action="store_true",
        default=os.environ.get("AGENT_ENHANCER_REQUIRE_OWNED_AUTOMATION") == "1",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("--input", default="-")
    invoke_parser = subparsers.add_parser("invoke")
    invoke_parser.add_argument("--slug", required=True, choices=sorted(ALLOWED_TOOLS))
    invoke_parser.add_argument("--input", default="-")
    invoke_parser.add_argument("--idempotency-key")
    blueprint_parser = subparsers.add_parser("checkpoint-blueprint")
    blueprint_parser.add_argument("--scope", default="workflow")
    blueprint_parser.add_argument("--operation-id", required=True)
    blueprint_parser.add_argument("--holders", nargs="+", required=True)
    blueprint_parser.add_argument("--namespace-uuid")
    blueprint_parser.add_argument("--claim-ttl-seconds", type=int, default=120)
    blueprint_parser.add_argument("--state-ttl-seconds", type=int, default=3_600)
    blueprint_parser.add_argument("--output")
    checkpoint_parser = subparsers.add_parser("checkpoint-step")
    checkpoint_parser.add_argument("--blueprint", required=True)
    checkpoint_parser.add_argument("--holder", required=True)
    checkpoint_parser.add_argument(
        "--step",
        required=True,
        choices=(
            "claim",
            "start",
            "uncertain",
            "verify-after-attempt",
            "verify-after-uncertain",
            "fail-before-attempt",
            "fail-after-attempt",
            "fail-after-uncertain",
            "status",
        ),
    )
    args = parser.parse_args(argv)
    client = DirectToolClient(
        args.base_url,
        source=args.source,
        require_owned_automation=args.require_owned_automation,
    )
    try:
        if args.command == "plan":
            result = plan_on_demand(_read_json(args.input), client)
        elif args.command == "invoke":
            result = invoke_tool(
                args.slug,
                _read_json(args.input),
                args.idempotency_key,
                client,
            )
        elif args.command == "checkpoint-blueprint":
            blueprint = build_checkpoint_blueprint(
                scope=args.scope,
                operation_id=args.operation_id,
                holder_labels=args.holders,
                namespace_uuid=args.namespace_uuid,
                claim_ttl_seconds=args.claim_ttl_seconds,
                state_ttl_seconds=args.state_ttl_seconds,
            )
            if args.output:
                Path(args.output).write_text(
                    json.dumps(blueprint, indent=2) + "\n",
                    encoding="utf-8",
                )
            result = {
                "decision": "checkpoint-blueprint",
                "remote_planner_calls": 0,
                "remote_coordination_calls": 0,
                "output": args.output,
                "holder_count": len(blueprint["holders"]),
                "namespace": blueprint["namespace"],
                "workflow_key": blueprint["workflow_key"],
            }
            if not args.output:
                result["blueprint"] = blueprint
        else:
            result = invoke_checkpoint_blueprint_step(
                _read_json(args.blueprint),
                holder_label=args.holder,
                step=args.step,
                client=client,
            )
    except (
        json.JSONDecodeError,
        OSError,
        OnDemandError,
    ) as error:
        code = getattr(error, "code", "INVALID_INPUT")
        _emit(
            {
                "ok": False,
                "error": {
                    "code": code,
                    "message": str(error),
                },
            }
        )
        return 2
    _emit({"ok": True, **result})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
