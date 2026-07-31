#!/usr/bin/env python3
"""Deterministic tests for the v1.7 diagnostic runner."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).with_name("run.py")
SPEC = importlib.util.spec_from_file_location("sidecar_v17_diagnostic", MODULE_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def row(scenario, condition, pair, *, tokens=100, latency=100, tool=None):
    return {
        "scenario": scenario,
        "condition": (
            "without-sidecar" if condition == "no-sidecar" else "with-sidecar"
        ),
        "diagnostic_condition": condition,
        "pair": pair,
        "verified": True,
        "external_attempts": 1 if scenario == "overlapping-workers" else 0,
        "duplicate_mutations": 0,
        "conflicting_actions": 0,
        "provider_rejections": 0,
        "unresolved_ambiguous": 0,
        "model_input_tokens": tokens,
        "wall_clock_ms": latency,
        "adapter_calls": 0,
        "sidecar_calls": 0,
        "sidecar_tools": [tool] if tool else [],
        "host_return_code": 0,
        "host_timed_out": False,
        "host_event_errors": 0,
        "host_policy_declines": 0,
        "unexpected_mcp_calls": 0,
        "unmarked_sidecar_invocations": 0,
        "final_response_present": True,
    }


class DiagnosticRunnerTests(unittest.TestCase):
    def test_schedule_contains_every_condition_for_45_runs(self):
        plan = runner._load_plan()
        schedule = runner._schedule(plan)
        self.assertEqual(len(schedule), 45)
        for scenario, trials in plan["scenarios"].items():
            for trial in range(1, trials + 1):
                self.assertEqual(
                    {
                        condition
                        for selected, condition, pair in schedule
                        if selected == scenario and pair == trial
                    },
                    set(runner.CONDITIONS),
                )

    def test_report_keeps_safety_and_efficiency_separate(self):
        rows = []
        for condition in runner.CONDITIONS:
            for trial in range(1, 11):
                rows.append(
                    row(
                        "overlapping-workers",
                        condition,
                        trial,
                        tokens=70 if condition == "skill-v1.7.0" else 100,
                        latency=80 if condition == "skill-v1.7.0" else 100,
                        tool=(
                            "workflow-checkpoint"
                            if condition == "skill-v1.7.0"
                            else None
                        ),
                    )
                )
            for trial in range(1, 6):
                rows.append(row("low-risk-abstention", condition, trial))

        report = runner._build_report(runner._load_plan(), rows, {})
        self.assertTrue(report["complete"])
        self.assertEqual(report["safety_status"], "passed")
        self.assertEqual(report["efficiency_status"], "passed")
        self.assertEqual(
            report["summaries"]["skill-v1.7.0"][
                "overlap_checkpoint_selected_runs"
            ],
            10,
        )


if __name__ == "__main__":
    unittest.main()
