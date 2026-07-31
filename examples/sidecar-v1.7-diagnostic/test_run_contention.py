#!/usr/bin/env python3
"""Unit tests for the v1.7.2 contention report."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "sidecar_v172_contention",
    HERE / "run_contention.py",
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to load contention runner")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ContentionReportTests(unittest.TestCase):
    def test_complete_candidate_with_checkpoint_passes(self) -> None:
        plan = MODULE.BASE._load_json(MODULE.PLAN_PATH)
        baseline = MODULE.BASE._load_json(MODULE.BASELINE_PATH)
        previous = MODULE.BASE._load_json(MODULE.PREVIOUS_PATH)
        candidate = []
        for original in previous["candidate_attempts"]:
            if not MODULE.BASE._valid(original):
                continue
            row = deepcopy(original)
            row["diagnostic_condition"] = "skill-v1.7.2"
            row["skill_version"] = "1.7.2"
            row["verified"] = True
            row["duplicate_mutations"] = 0
            row["conflicting_actions"] = 0
            row["provider_rejections"] = 0
            row["unresolved_ambiguous"] = 0
            if row["scenario"] == "overlapping-workers":
                row["sidecar_tools"] = [
                    "workflow-checkpoint",
                    "workflow-guard-planner",
                ]
                row["external_attempts"] = 1
            else:
                row["sidecar_tools"] = []
                row["adapter_calls"] = 0
                row["sidecar_calls"] = 0
            candidate.append(row)

        report = MODULE._build_report(
            plan,
            baseline,
            previous,
            candidate,
            {"candidate_skill_tag": "v1.7.2"},
            None,
        )

        self.assertTrue(report["complete"])
        self.assertEqual(report["safety_status"], "passed")
        self.assertEqual(
            report["checkpoint_adherence_change"],
            {"skill-v1.7.1": 6, "skill-v1.7.2": 10, "denominator": 10},
        )


if __name__ == "__main__":
    unittest.main()
