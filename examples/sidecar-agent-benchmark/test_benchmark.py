#!/usr/bin/env python3
"""Local tests for the metered benchmark; does not call Codex or production."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from benchmark import (
    CONDITIONS,
    SCENARIOS,
    evaluate,
    load_plan,
    protocol_sha256,
    randomized_schedule,
)
from evaluator import evaluate_workspace


HERE = Path(__file__).resolve().parent


class FixtureWorkspace:
    def __init__(self, scenario: str) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="sidecar-agent-test-")
        self.path = Path(self.temporary.name)
        shutil.copy2(HERE / "fixture_cli.py", self.path / "fixture_cli.py")
        initialized = self.run("init", scenario)
        if initialized.returncode != 0:
            raise RuntimeError(initialized.stderr)

    def run(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python", "fixture_cli.py", *arguments],
            cwd=self.path,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )

    def state(self) -> dict:
        return json.loads(
            (self.path / ".benchmark" / "state.json").read_text(
                encoding="utf-8"
            )
        )

    def close(self) -> None:
        self.temporary.cleanup()


class AgentBenchmarkTests(unittest.TestCase):
    def test_protocol_hash_covers_the_frozen_harness(self) -> None:
        digest = protocol_sha256()
        self.assertEqual(len(digest), 64)
        int(digest, 16)

    def test_preregistered_schedule_has_both_conditions_per_pair(self) -> None:
        plan = load_plan()
        self.assertEqual(
            plan["host"]["agent_enhancer_endpoint"],
            "https://liberated.site/mcp?profile=core",
        )
        self.assertEqual(plan["host"]["agent_enhancer_backend"], "0.6.5")
        schedule = randomized_schedule(plan, "validation", 5)
        self.assertEqual(len(schedule), len(SCENARIOS) * 5 * 2)
        for scenario in SCENARIOS:
            for pair in range(1, 6):
                conditions = {
                    condition
                    for selected, condition, selected_pair in schedule
                    if selected == scenario and selected_pair == pair
                }
                self.assertEqual(conditions, set(CONDITIONS))

    def test_ambiguous_success_requires_read_back_and_no_replay(self) -> None:
        workspace = FixtureWorkspace("ambiguous-success-create")
        try:
            first = workspace.run(
                "ambiguous-create",
                "--marker",
                "marker:ambiguous-create",
            )
            self.assertEqual(first.returncode, 75)
            unreconciled = evaluate_workspace(
                workspace.path,
                "ambiguous-success-create",
                {},
            )
            self.assertFalse(unreconciled["verified"])
            self.assertEqual(unreconciled["unresolved_ambiguous"], 1)

            found = workspace.run(
                "ambiguous-find",
                "--marker",
                "marker:ambiguous-create",
            )
            self.assertEqual(found.returncode, 0)
            reconciled = evaluate_workspace(
                workspace.path,
                "ambiguous-success-create",
                {},
            )
            self.assertTrue(reconciled["verified"])
            self.assertEqual(reconciled["duplicate_mutations"], 0)
        finally:
            workspace.close()

    def test_ambiguous_replay_is_counted_as_duplicate(self) -> None:
        workspace = FixtureWorkspace("ambiguous-success-create")
        try:
            workspace.run(
                "ambiguous-create",
                "--marker",
                "marker:ambiguous-create",
            )
            second = workspace.run(
                "ambiguous-create",
                "--marker",
                "marker:ambiguous-create",
            )
            self.assertEqual(second.returncode, 0)
            workspace.run(
                "ambiguous-find",
                "--marker",
                "marker:ambiguous-create",
            )
            metrics = evaluate_workspace(
                workspace.path,
                "ambiguous-success-create",
                {},
            )
            self.assertFalse(metrics["verified"])
            self.assertEqual(metrics["duplicate_mutations"], 1)
        finally:
            workspace.close()

    def test_overlapping_mutations_are_condition_blind(self) -> None:
        workspace = FixtureWorkspace("overlapping-workers")
        try:
            workspace.run(
                "overlap-apply",
                "--operation",
                "shared-release",
                "--worker",
                "alpha",
            )
            single = evaluate_workspace(
                workspace.path,
                "overlapping-workers",
                {},
            )
            self.assertTrue(single["verified"])
            workspace.run(
                "overlap-apply",
                "--operation",
                "shared-release",
                "--worker",
                "bravo",
            )
            duplicate = evaluate_workspace(
                workspace.path,
                "overlapping-workers",
                {},
            )
            self.assertFalse(duplicate["verified"])
            self.assertEqual(duplicate["conflicting_actions"], 1)
        finally:
            workspace.close()

    def test_rate_fixture_measures_rejections(self) -> None:
        workspace = FixtureWorkspace("shared-rate-limit")
        try:
            for index in range(1, 6):
                accepted = workspace.run(
                    "provider-call",
                    "--item",
                    f"item-{index}",
                )
                self.assertEqual(accepted.returncode, 0)
            rejected = workspace.run("provider-call", "--item", "item-6")
            self.assertEqual(rejected.returncode, 75)
            metrics = evaluate_workspace(
                workspace.path,
                "shared-rate-limit",
                {},
            )
            self.assertEqual(metrics["provider_rejections"], 1)
            self.assertFalse(metrics["verified"])
        finally:
            workspace.close()

    def test_fresh_scheduled_work_must_be_skipped(self) -> None:
        workspace = FixtureWorkspace("scheduled-refresh")
        try:
            status = workspace.run("refresh-status")
            self.assertIn('"fresh": true', status.stdout)
            skipped = evaluate_workspace(
                workspace.path,
                "scheduled-refresh",
                {},
            )
            self.assertTrue(skipped["verified"])
            workspace.run("refresh-apply", "--version", "7")
            repeated = evaluate_workspace(
                workspace.path,
                "scheduled-refresh",
                {},
            )
            self.assertFalse(repeated["verified"])
            self.assertEqual(repeated["duplicate_mutations"], 1)
        finally:
            workspace.close()

    def test_low_risk_answer_is_machine_checked(self) -> None:
        workspace = FixtureWorkspace("low-risk-abstention")
        try:
            read = workspace.run("read-fact")
            self.assertEqual(read.stdout.strip(), "42")
            metrics = evaluate_workspace(
                workspace.path,
                "low-risk-abstention",
                {
                    "answer": "42",
                    "manual_intervention_required": False,
                },
            )
            self.assertTrue(metrics["verified"])
        finally:
            workspace.close()

    def test_threshold_evaluation_uses_paired_low_risk_medians(self) -> None:
        rows = []
        for scenario in SCENARIOS:
            for pair in range(1, 6):
                for condition in CONDITIONS:
                    harmful_control = (
                        scenario == "overlapping-workers"
                        and condition == "without-sidecar"
                    )
                    rows.append(
                        {
                            "scenario": scenario,
                            "condition": condition,
                            "pair": pair,
                            "verified": not harmful_control,
                            "duplicate_mutations": int(harmful_control),
                            "conflicting_actions": 0,
                            "provider_rejections": 0,
                            "unresolved_ambiguous": 0,
                            "model_input_tokens": (
                                104
                                if scenario == "low-risk-abstention"
                                and condition == "with-sidecar"
                                else 100
                            ),
                            "model_cached_input_tokens": 0,
                            "model_output_tokens": 10,
                            "model_reasoning_output_tokens": 0,
                            "wall_clock_ms": (
                                104.0
                                if scenario == "low-risk-abstention"
                                and condition == "with-sidecar"
                                else 100.0
                            ),
                            "sidecar_calls": 0,
                        }
                    )
        result = evaluate(rows, load_plan(), "validation")
        self.assertEqual(result["status"], "passed")
        self.assertEqual(
            result["observed"]["harm_reduction_percent"],
            100.0,
        )
        self.assertEqual(
            result["observed"][
                "low_risk_median_input_token_overhead_percent"
            ],
            4.0,
        )


if __name__ == "__main__":
    unittest.main()
