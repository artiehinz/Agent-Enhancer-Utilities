#!/usr/bin/env python3
"""Tests for the on-demand sidecar activation boundary."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "on_demand_sidecar",
    HERE / "run.py",
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to load on-demand example")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FakePlannerClient:
    def __init__(self) -> None:
        self.calls = 0

    def invoke(self, slug, contract, idempotency_key=None):
        self.calls += 1
        return {
            "slug": slug,
            "result": MODULE.LOCAL_PLANNER.plan_workflow(contract),
            "request_id": "req_test",
            "owned_automation_excluded": True,
            "remote_calls": self.calls,
        }


class OnDemandSidecarTests(unittest.TestCase):
    def test_low_risk_abstention_makes_no_remote_call(self) -> None:
        client = FakePlannerClient()
        result = MODULE.plan_on_demand(
            MODULE.LOW_RISK_CONTRACT,
            client,
        )
        self.assertEqual(result["decision"], "no-sidecar")
        self.assertEqual(result["activation"], "local-abstention")
        self.assertEqual(result["remote_planner_calls"], 0)
        self.assertEqual(client.calls, 0)

    def test_risk_bearing_work_activates_existing_service_once(self) -> None:
        client = FakePlannerClient()
        result = MODULE.plan_on_demand(
            MODULE.HIGH_RISK_CONTRACT,
            client,
        )
        self.assertEqual(result["decision"], "sidecar")
        self.assertEqual(
            result["activation"],
            "remote-after-local-selection",
        )
        self.assertEqual(result["plan"]["profile"], "create-once")
        self.assertEqual(result["remote_planner_calls"], 1)
        self.assertEqual(client.calls, 1)

    def test_local_and_remote_plan_drift_fails_closed(self) -> None:
        class DriftedClient(FakePlannerClient):
            def invoke(self, slug, contract, idempotency_key=None):
                result = super().invoke(slug, contract, idempotency_key)
                result["result"] = {
                    **result["result"],
                    "guarantee": "best-effort",
                }
                return result

        with self.assertRaisesRegex(
            MODULE.ADAPTER.OnDemandError,
            "disagree on guarantee",
        ):
            MODULE.plan_on_demand(
                MODULE.HIGH_RISK_CONTRACT,
                DriftedClient(),
            )


if __name__ == "__main__":
    unittest.main()
