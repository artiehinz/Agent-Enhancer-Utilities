#!/usr/bin/env python3
"""Tests for the local Workflow Guard Planner reference."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).with_name("plan_workflow.py")
SPEC = importlib.util.spec_from_file_location("plan_workflow", MODULE_PATH)
assert SPEC and SPEC.loader
planner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(planner)
OUTPUT_SCHEMA = json.loads(
    (
        Path(__file__).resolve().parents[3]
        / "docs"
        / "schemas"
        / "workflow-guard-planner.output.schema.json"
    ).read_text(encoding="utf-8")
)


def base_contract(**overrides):
    contract = {
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
    contract.update(overrides)
    return contract


class PlannerTests(unittest.TestCase):
    def assert_output_shape(self, result):
        self.assertEqual(set(result), set(OUTPUT_SCHEMA["required"]))
        self.assertFalse(set(result) - set(OUTPUT_SCHEMA["properties"]))
        if result["profile"] is not None:
            self.assertIn(
                result["profile"],
                OUTPUT_SCHEMA["properties"]["profile"]["anyOf"][0]["enum"],
            )
        if result["guarantee"] is not None:
            self.assertIn(
                result["guarantee"],
                OUTPUT_SCHEMA["properties"]["guarantee"]["anyOf"][0]["enum"],
            )

    def test_abstains_from_one_time_read(self):
        result = planner.plan_workflow(base_contract())
        self.assert_output_shape(result)
        self.assertEqual(result["decision"], "no-sidecar")
        self.assertEqual(result["decision_reason"], "ordinary-one-time-low-risk")
        self.assertIsNone(result["profile"])
        self.assertIsNone(result["guarantee"])
        self.assertEqual(result["stages"], [])

    def test_searchable_scheduled_create(self):
        result = planner.plan_workflow(
            base_contract(
                operation_class="create",
                duplicate_harm="material",
                parallel_workers=3,
                scheduled=True,
                retry_possible=True,
                destination_search="eventual",
                stable_marker=True,
                read_after_write=True,
                shared_rate_limit=True,
                maximum_concurrency=2,
                compensation="manual",
            )
        )
        self.assert_output_shape(result)
        self.assertEqual(result["profile"], "create-once")
        self.assertEqual(result["decision"], "sidecar")
        self.assertEqual(result["additional_profiles"], ["scheduled-run"])
        self.assertEqual(result["guarantee"], "duplicate-resistant")
        actions = [stage["action"] for stage in result["stages"]]
        self.assertLess(actions.index("read_after_write"), actions.index("mark_seen_after_verification"))
        self.assertIn("destination_search_is_eventually_consistent", result["residual_risks"])

    def test_batch_create_composes_fanout_and_schedule(self):
        result = planner.plan_workflow(
            base_contract(
                operation_class="batch",
                item_operation_class="create",
                duplicate_harm="material",
                parallel_workers=4,
                scheduled=True,
                retry_possible=True,
                destination_search="strong",
                stable_marker=True,
                read_after_write=True,
                shared_rate_limit=True,
                maximum_concurrency=2,
            )
        )
        self.assert_output_shape(result)
        self.assertEqual(result["profile"], "create-once")
        self.assertEqual(
            result["additional_profiles"],
            ["fan-out-bounded", "scheduled-run"],
        )
        self.assertEqual(result["guarantee"], "duplicate-resistant")
        actions = [stage["action"] for stage in result["stages"]]
        self.assertIn("acquire_semaphore", actions)
        self.assertIn("acquire_run_lock", actions)
        self.assertIn("consume_rate_gate", actions)
        self.assertIn("arrive_barrier", actions)

    def test_unqueryable_send_stops_after_timeout(self):
        result = planner.plan_workflow(
            base_contract(
                operation_class="send",
                duplicate_harm="irreversible",
                parallel_workers=3,
                retry_possible=True,
            )
        )
        self.assert_output_shape(result)
        self.assertEqual(result["profile"], "send-at-most-once")
        self.assertEqual(result["guarantee"], "best-effort")
        self.assertEqual(result["timeout_recovery"], "stop_for_review")
        self.assertIn(
            "uncertain_irreversible_action_requires_review",
            result["residual_risks"],
        )

    def test_parallel_read_is_bounded(self):
        result = planner.plan_workflow(
            base_contract(
                parallel_workers=8,
                shared_rate_limit=True,
                maximum_concurrency=3,
            )
        )
        self.assert_output_shape(result)
        self.assertEqual(result["profile"], "fan-out-bounded")
        self.assertEqual(result["guarantee"], "rate/concurrency-bounded")
        actions = [stage["action"] for stage in result["stages"]]
        self.assertIn("acquire_semaphore", actions)
        self.assertIn("consume_rate_gate", actions)
        self.assertIn("arrive_barrier", actions)

    def test_shared_update_reports_unguarded_writer_risk(self):
        result = planner.plan_workflow(
            base_contract(
                operation_class="update",
                duplicate_harm="material",
                parallel_workers=2,
                retry_possible=True,
                read_after_write=True,
            )
        )
        self.assert_output_shape(result)
        self.assertEqual(result["profile"], "update-safely")
        self.assertEqual(result["guarantee"], "concurrency-safe")
        self.assertIn(
            "unguarded_writer_can_bypass_sidecar",
            result["residual_risks"],
        )

    def test_provider_idempotency_is_provider_backed(self):
        result = planner.plan_workflow(
            base_contract(
                operation_class="create",
                duplicate_harm="material",
                retry_possible=True,
                provider_idempotency="request_key",
                read_after_write=True,
            )
        )
        self.assert_output_shape(result)
        self.assertEqual(result["guarantee"], "provider-idempotent")
        self.assertIn("cross_plugin_exactly_once", result["unsupported_claims"])

    def test_batch_requires_item_operation(self):
        with self.assertRaises(planner.PlannerError) as context:
            planner.plan_workflow(base_contract(operation_class="batch"))
        self.assertEqual(context.exception.code, "INVALID_INPUT")

    def test_closed_contract_rejects_unknown_field(self):
        with self.assertRaises(planner.PlannerError) as context:
            planner.plan_workflow(base_contract(raw_document="not allowed"))
        self.assertEqual(context.exception.code, "INVALID_INPUT")

    def test_unqueryable_retryable_create_is_best_effort(self):
        result = planner.plan_workflow(
            base_contract(
                operation_class="create",
                duplicate_harm="material",
                parallel_workers=4,
                retry_possible=True,
            )
        )
        self.assert_output_shape(result)
        self.assertEqual(result["guarantee"], "best-effort")
        self.assertIn("create", [stage["action"] for stage in result["stages"]])
        self.assertNotIn(
            "create_if_absent",
            [stage["action"] for stage in result["stages"]],
        )

    def test_concurrency_cap_cannot_exceed_workers(self):
        with self.assertRaises(planner.PlannerError) as context:
            planner.plan_workflow(
                base_contract(
                    parallel_workers=2,
                    maximum_concurrency=3,
                )
            )
        self.assertEqual(context.exception.code, "INVALID_INPUT")


if __name__ == "__main__":
    unittest.main()
