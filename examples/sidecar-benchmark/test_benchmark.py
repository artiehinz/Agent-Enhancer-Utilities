#!/usr/bin/env python3
"""Contract and benchmark acceptance tests without third-party packages."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from adapters import ContractError, InMemoryReliabilityAdapter, opaque_id
from benchmark import SCENARIOS, build_report, load_plan


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


class AdapterTests(unittest.TestCase):
    def test_competing_claims_admit_one_holder(self) -> None:
        adapter = InMemoryReliabilityAdapter()
        operation = opaque_id("op", "shared-action")
        holder_a = opaque_id("holder", "a")
        holder_b = opaque_id("holder", "b")
        self.assertTrue(adapter.claim(operation, holder_a)[0])
        self.assertFalse(adapter.claim(operation, holder_b)[0])

    def test_uncertain_result_must_reconcile_before_verification(self) -> None:
        adapter = InMemoryReliabilityAdapter()
        operation = opaque_id("op", "uncertain-action")
        holder = opaque_id("holder", "a")
        adapter.claim(operation, holder)
        adapter.transition(operation, holder, "external_attempt_started")
        uncertain = adapter.transition(
            operation,
            holder,
            "external_result_uncertain",
        )
        self.assertFalse(uncertain["external_proof"])
        verified = adapter.transition(operation, holder, "caller_verified")
        self.assertEqual(verified["stage"], "caller_verified")
        self.assertFalse(verified["external_proof"])

    def test_invalid_transition_fails_closed(self) -> None:
        adapter = InMemoryReliabilityAdapter()
        operation = opaque_id("op", "invalid-transition")
        holder = opaque_id("holder", "a")
        adapter.claim(operation, holder)
        with self.assertRaises(ContractError):
            adapter.transition(operation, holder, "compensated")


class BenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plan = load_plan(HERE / "preregistered-plan.json")
        cls.report = build_report(cls.plan)

    def aggregate(self, scenario: str, condition: str) -> dict[str, object]:
        return next(
            row
            for row in self.report["published"]["aggregates"]
            if row["scenario"] == scenario and row["condition"] == condition
        )

    def test_pre_registered_run_counts(self) -> None:
        self.assertEqual(set(SCENARIOS), set(self.plan["scenarios"]))
        self.assertEqual(self.report["validation"]["rows_executed"], 50)
        self.assertEqual(len(self.report["published"]["rows"]), 200)
        self.assertTrue(
            all(
                row["runs"] == 20
                for row in self.report["published"]["aggregates"]
            )
        )

    def test_ambiguous_success_does_not_replay_guarded_mutation(self) -> None:
        unguarded = self.aggregate(
            "ambiguous-success-create",
            "without-sidecar",
        )
        guarded = self.aggregate(
            "ambiguous-success-create",
            "with-sidecar",
        )
        self.assertEqual(unguarded["duplicate_mutations"], 20)
        self.assertEqual(guarded["duplicate_mutations"], 0)
        self.assertEqual(guarded["unresolved_ambiguous"], 0)
        self.assertEqual(guarded["verified_runs"], 20)

    def test_competing_workers_cross_write_boundary_once(self) -> None:
        unguarded = self.aggregate("overlapping-workers", "without-sidecar")
        guarded = self.aggregate("overlapping-workers", "with-sidecar")
        self.assertEqual(unguarded["conflicting_actions"], 20)
        self.assertEqual(guarded["conflicting_actions"], 0)
        self.assertEqual(guarded["external_attempts"], 20)

    def test_rate_gate_prevents_provider_rejection(self) -> None:
        unguarded = self.aggregate("shared-rate-limit", "without-sidecar")
        guarded = self.aggregate("shared-rate-limit", "with-sidecar")
        self.assertEqual(unguarded["provider_rejections"], 100)
        self.assertEqual(guarded["provider_rejections"], 0)

    def test_freshness_suppresses_redundant_refresh(self) -> None:
        unguarded = self.aggregate("scheduled-refresh", "without-sidecar")
        guarded = self.aggregate("scheduled-refresh", "with-sidecar")
        self.assertEqual(unguarded["duplicate_mutations"], 20)
        self.assertEqual(guarded["duplicate_mutations"], 0)

    def test_low_risk_path_abstains_without_sidecar_calls(self) -> None:
        guarded = self.aggregate("low-risk-abstention", "with-sidecar")
        self.assertEqual(guarded["sidecar_calls"], 0)
        rows = [
            row
            for row in self.report["published"]["rows"]
            if row["scenario"] == "low-risk-abstention"
            and row["condition"] == "with-sidecar"
        ]
        self.assertTrue(all(row["abstained"] for row in rows))

    def test_model_usage_is_explicitly_unavailable(self) -> None:
        self.assertTrue(
            all(
                row["model_input_tokens"] is None
                and row["model_output_tokens"] is None
                and row["model_cost_usd"] is None
                for row in self.report["published"]["rows"]
            )
        )

    def test_contract_schema_is_closed_and_defines_public_types(self) -> None:
        schema = json.loads(
            (
                ROOT
                / "docs"
                / "schemas"
                / "reliability-sidecar-contract-v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["schema_revision"]["const"], "2")
        self.assertEqual(
            set(schema["$defs"]),
            {
                "OpaqueOperationId",
                "OpaqueHolderId",
                "GuaranteeLabel",
                "CapabilityFactsV1",
                "GuardPlanV1",
                "CheckpointV1",
                "EvidenceV1",
                "ReliabilityReportV1",
            },
        )
        for public_type in (
            "CapabilityFactsV1",
            "GuardPlanV1",
            "CheckpointV1",
            "EvidenceV1",
            "ReliabilityReportV1",
        ):
            self.assertFalse(schema["$defs"][public_type]["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
