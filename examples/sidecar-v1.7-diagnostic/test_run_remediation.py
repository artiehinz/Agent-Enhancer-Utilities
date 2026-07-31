#!/usr/bin/env python3
"""Unit tests for the separate v1.7.1 remediation report."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "sidecar_v171_remediation",
    HERE / "run_remediation.py",
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to load remediation runner")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RemediationReportTests(unittest.TestCase):
    def test_complete_safe_candidate_passes_frozen_gates(self) -> None:
        plan = MODULE._load_json(MODULE.PLAN_PATH)
        source = MODULE._load_json(MODULE.SOURCE_PATH)
        baseline = [
            row
            for row in source["rows"]
            if row.get("diagnostic_condition") == "skill-v1.6.0"
            and MODULE._valid(row)
        ]
        candidate = []
        for original in baseline:
            row = deepcopy(original)
            row["diagnostic_condition"] = "skill-v1.7.1"
            row["skill_version"] = "1.7.1"
            row["verified"] = True
            row["duplicate_mutations"] = 0
            row["conflicting_actions"] = 0
            row["provider_rejections"] = 0
            row["unresolved_ambiguous"] = 0
            row["sidecar_tools"] = (
                ["workflow-checkpoint", "workflow-guard-planner"]
                if row["scenario"] == "overlapping-workers"
                else []
            )
            row["external_attempts"] = (
                1 if row["scenario"] == "overlapping-workers" else 0
            )
            row["adapter_calls"] = (
                4 if row["scenario"] == "overlapping-workers" else 0
            )
            row["sidecar_calls"] = (
                4 if row["scenario"] == "overlapping-workers" else 0
            )
            row["model_input_tokens"] = max(
                1, int(original["model_input_tokens"] * 0.5)
            )
            row["wall_clock_ms"] = max(1, original["wall_clock_ms"] * 0.5)
            candidate.append(row)

        report = MODULE._build_report(
            plan,
            source,
            candidate,
            {"candidate_skill_tag": "v1.7.1"},
            None,
        )

        self.assertTrue(report["complete"])
        self.assertEqual(report["safety_status"], "passed")
        self.assertEqual(report["efficiency_status"], "passed")
        self.assertEqual(report["candidate_summary"]["overlap_runs"], 10)
        self.assertEqual(report["candidate_summary"]["low_risk_runs"], 5)


if __name__ == "__main__":
    unittest.main()
