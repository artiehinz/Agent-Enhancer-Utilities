#!/usr/bin/env python3
"""Tests for the skills-first on-demand HTTP adapter."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import threading
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "agent_enhancer_on_demand",
    HERE / "on_demand.py",
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to load on-demand adapter")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

LOW_RISK = {
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
HIGH_RISK = {
    **LOW_RISK,
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


class FakeClient:
    def __init__(self) -> None:
        self.calls = 0
        self.requests = []

    def invoke(self, slug, tool_input, idempotency_key=None):
        self.calls += 1
        self.requests.append((slug, tool_input, idempotency_key))
        if slug == "workflow-guard-planner":
            result = MODULE.LOCAL_PLANNER.plan_workflow(tool_input)
        else:
            result = {"accepted": True}
        return {
            "slug": slug,
            "result": result,
            "request_id": "req_test",
            "owned_automation_excluded": True,
            "remote_calls": self.calls,
        }


class ContentionClient(FakeClient):
    def __init__(self) -> None:
        super().__init__()
        self.owner = None
        self.lock = threading.Lock()

    def invoke(self, slug, tool_input, idempotency_key=None):
        with self.lock:
            self.calls += 1
            self.requests.append((slug, tool_input, idempotency_key))
            holder = tool_input["holder"]
            if self.owner is None:
                self.owner = holder
                disposition = "acquired"
            elif holder == self.owner:
                disposition = "reused"
            else:
                disposition = "write_execution_in_progress"
        return {
            "slug": slug,
            "result": {"claim_disposition": disposition},
            "request_id": "req_test",
            "owned_automation_excluded": True,
            "remote_calls": self.calls,
        }


class UnsafeContentionClient(ContentionClient):
    def invoke(self, slug, tool_input, idempotency_key=None):
        with self.lock:
            self.calls += 1
            self.requests.append((slug, tool_input, idempotency_key))
        return {
            "slug": slug,
            "result": {"claim_disposition": "acquired"},
            "request_id": "req_unsafe",
            "owned_automation_excluded": True,
            "remote_calls": self.calls,
        }


class OnDemandTests(unittest.TestCase):
    def test_low_risk_abstains_without_constructing_a_client(self) -> None:
        result = MODULE.plan_on_demand(LOW_RISK)
        self.assertEqual(result["activation"], "local-abstention")
        self.assertEqual(result["remote_planner_calls"], 0)
        self.assertIsNone(result["execution_recipe"])

    def test_risk_bearing_plan_calls_hosted_planner_once(self) -> None:
        client = FakeClient()
        result = MODULE.plan_on_demand(HIGH_RISK, client)
        self.assertEqual(result["activation"], "remote-after-local-selection")
        self.assertEqual(result["remote_planner_calls"], 1)
        self.assertEqual(client.calls, 1)
        self.assertEqual(client.requests[0][0], "workflow-guard-planner")
        self.assertEqual(
            result["execution_recipe"],
            {
                "required_guard": "workflow-checkpoint",
                "external_preflight": ["search_stable_marker"],
                "attempt_boundary_transition": (
                    "claimed_to_external_attempt_started"
                ),
                "verification": [
                    "read_after_write",
                    "record_caller_verified",
                ],
                "uncertainty_recovery": (
                    "checkpoint_uncertain_then_search_marker"
                ),
                "prohibited_action": (
                    "blind_external_retry_after_uncertain_write"
                ),
                "checkpoint_step_command": "checkpoint-step",
                "prepare_command": "checkpoint-prepare",
                "namespace_rule": "<scope>:<fresh UUID v4>",
            },
        )

    def test_checkpoint_blueprint_builds_valid_first_generation_steps(self) -> None:
        blueprint = MODULE.build_checkpoint_blueprint(
            scope="bench",
            operation_id="operation_0123456789abcdef",
            holder_labels=["alpha", "bravo"],
            namespace_uuid="6f0a1e7e-e446-46f1-88ab-bddef15f89a2",
        )
        self.assertEqual(
            blueprint["namespace"],
            "bench:6f0a1e7e-e446-46f1-88ab-bddef15f89a2",
        )
        self.assertEqual(blueprint["generation"], 1)
        self.assertNotIn("operation_0123456789abcdef", str(blueprint))
        self.assertNotEqual(
            blueprint["holders"]["alpha"],
            blueprint["holders"]["bravo"],
        )
        self.assertLess(len(str(blueprint)), 2_000)
        client = FakeClient()
        for step in (
            "claim",
            "start",
            "uncertain",
            "verify-after-attempt",
            "verify-after-uncertain",
            "fail-before-attempt",
            "fail-after-attempt",
            "fail-after-uncertain",
            "status",
        ):
            MODULE.invoke_checkpoint_blueprint_step(
                blueprint,
                holder_label="alpha",
                step=step,
                client=client,
            )

    def test_checkpoint_blueprint_invokes_selected_step_only(self) -> None:
        blueprint = MODULE.build_checkpoint_blueprint(
            scope="bench",
            operation_id="operation_0123456789abcdef",
            holder_labels=["alpha"],
            namespace_uuid="6f0a1e7e-e446-46f1-88ab-bddef15f89a2",
        )
        client = FakeClient()
        result = MODULE.invoke_checkpoint_blueprint_step(
            blueprint,
            holder_label="alpha",
            step="claim",
            client=client,
        )
        self.assertEqual(result["slug"], "workflow-checkpoint")
        self.assertEqual(result["blueprint_step"], "claim")
        self.assertEqual(len(client.requests), 1)
        self.assertEqual(client.requests[0][1]["action"], "claim")

    def test_checkpoint_contention_returns_exactly_one_winner(self) -> None:
        blueprint = MODULE.build_checkpoint_blueprint(
            scope="bench",
            operation_id="operation_0123456789abcdef",
            holder_labels=["alpha", "bravo", "charlie"],
            namespace_uuid="6f0a1e7e-e446-46f1-88ab-bddef15f89a2",
        )
        result = MODULE.contend_checkpoint_blueprint(
            blueprint,
            client=ContentionClient(),
        )
        self.assertEqual(result["decision"], "checkpoint-contend")
        self.assertEqual(len(result["blocked_holders"]), 2)
        self.assertEqual(
            result["claim_dispositions"][result["winner"]],
            "acquired",
        )
        self.assertEqual(result["remote_coordination_calls"], 3)

    def test_checkpoint_contention_fails_closed_on_multiple_winners(self) -> None:
        blueprint = MODULE.build_checkpoint_blueprint(
            scope="bench",
            operation_id="operation_0123456789abcdef",
            holder_labels=["alpha", "bravo"],
            namespace_uuid="6f0a1e7e-e446-46f1-88ab-bddef15f89a2",
        )
        with self.assertRaisesRegex(
            MODULE.OnDemandError,
            "did not prove exactly one admitted holder",
        ):
            MODULE.contend_checkpoint_blueprint(
                blueprint,
                client=UnsafeContentionClient(),
            )

    def test_checkpoint_evidence_fingerprint_matches_hosted_contract(self) -> None:
        request = {
            "action": "transition",
            "namespace": "bench:6f0a1e7e-e446-46f1-88ab-bddef15f89a2",
            "workflow_key": "workflow_0123456789abcdef",
            "holder": "holder_0123456789abcdef",
            "expected_generation": 1,
            "from_stage": "external_attempt_started",
            "to_stage": "caller_verified",
            "observation_key": "observation_0123456789abcdef",
            "evidence_type": "stable_marker_readback",
            "evidence_fingerprint": "hmac-sha256:" + "a" * 64,
        }
        MODULE.validate_tool_request(
            "workflow-checkpoint",
            request,
            "checkpoint_request_0001",
        )
        request["evidence_fingerprint"] = "a" * 64
        with self.assertRaisesRegex(MODULE.OnDemandError, "must be an opaque"):
            MODULE.validate_tool_request(
                "workflow-checkpoint",
                request,
                "checkpoint_request_0001",
            )

    def test_hosted_planner_request_accepts_contract_version_one(self) -> None:
        validated = MODULE.validate_tool_request(
            "workflow-guard-planner",
            HIGH_RISK,
            None,
        )
        self.assertEqual(validated["contract_version"], "1")

    def test_planner_drift_fails_closed(self) -> None:
        class DriftedClient(FakeClient):
            def invoke(self, slug, tool_input, idempotency_key=None):
                response = super().invoke(slug, tool_input, idempotency_key)
                response["result"] = {
                    **response["result"],
                    "guarantee": "best-effort",
                }
                return response

        with self.assertRaisesRegex(
            MODULE.OnDemandError,
            "disagree on guarantee",
        ):
            MODULE.plan_on_demand(HIGH_RISK, DriftedClient())

    def test_unknown_tool_is_rejected(self) -> None:
        with self.assertRaisesRegex(MODULE.OnDemandError, "allowlist"):
            MODULE.validate_tool_request(
                "send-email",
                {},
                "safe_idempotency_0001",
            )

    def test_unknown_fields_are_rejected_before_network(self) -> None:
        with self.assertRaisesRegex(MODULE.OnDemandError, "unknown fields"):
            MODULE.validate_tool_request(
                "penny-lock",
                {
                    "namespace": "bench:6f0a1e7e-e446-46f1-88ab-bddef15f89a2",
                    "key": "opaque_0123456789abcdef",
                    "owner": "holder_0123456789abcdef",
                    "ttl_seconds": 30,
                    "amount": 100,
                },
                "safe_idempotency_0001",
            )

    def test_stateful_call_requires_idempotency(self) -> None:
        with self.assertRaisesRegex(
            MODULE.OnDemandError,
            "stable idempotency_key",
        ):
            MODULE.validate_tool_request(
                "penny-lock",
                {
                    "namespace": "bench:6f0a1e7e-e446-46f1-88ab-bddef15f89a2",
                    "key": "opaque_0123456789abcdef",
                    "owner": "holder_0123456789abcdef",
                    "ttl_seconds": 30,
                },
                None,
            )

    def test_checkpoint_status_does_not_require_idempotency(self) -> None:
        MODULE.validate_tool_request(
            "workflow-checkpoint",
            {
                "action": "status",
                "namespace": "bench:6f0a1e7e-e446-46f1-88ab-bddef15f89a2",
                "workflow_key": "workflow_0123456789abcdef",
            },
            None,
        )

    def test_raw_identifiers_and_private_fields_are_rejected(self) -> None:
        cases = (
            (
                {
                    "namespace": "team",
                    "key": "job-42",
                    "owner": "agent-a",
                    "ttl_seconds": 30,
                },
                "must be an opaque",
            ),
            (
                {
                    "namespace": "bench:6f0a1e7e-e446-46f1-88ab-bddef15f89a2",
                    "key": "opaque_0123456789abcdef",
                    "owner": "holder_0123456789abcdef",
                    "message": "private task text",
                    "ttl_seconds": 30,
                },
                "private or destination data",
            ),
        )
        for tool_input, message in cases:
            with self.subTest(tool_input=tool_input):
                with self.assertRaisesRegex(MODULE.OnDemandError, message):
                    MODULE.validate_tool_request(
                        "penny-lock",
                        tool_input,
                        "safe_idempotency_0001",
                    )

    def test_invoke_tool_preserves_idempotency_key(self) -> None:
        client = FakeClient()
        result = MODULE.invoke_tool(
            "penny-lock",
            {
                "namespace": "bench:6f0a1e7e-e446-46f1-88ab-bddef15f89a2",
                "key": "opaque_0123456789abcdef",
                "owner": "holder_0123456789abcdef",
                "ttl_seconds": 30,
            },
            "safe_idempotency_0001",
            client,
        )
        self.assertTrue(result["result"]["accepted"])
        self.assertEqual(client.requests[0][2], "safe_idempotency_0001")


if __name__ == "__main__":
    unittest.main()
