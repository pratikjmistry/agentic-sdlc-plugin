#!/usr/bin/env python3
"""Fixture-based tests for score.py: determinism, band correctness, gate
precedence, verdict precedence, and weight redistribution.

Run: python3 -m unittest discover -s scripts/tests -v
(or: cd scripts && python3 -m unittest tests.test_score -v)
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import score  # noqa: E402

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
RUBRIC = score.load_rubric()


def load(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


class DeterminismTests(unittest.TestCase):
    def test_byte_identical_across_repeated_runs(self):
        for name in ["scored-strong.json", "scored-sparse-legacy.json", "scored-defer.json",
                     "scored-do-not-onboard.json", "scored-redistribution.json", "scored-only-layer1.json",
                     "scored-gates-pass-no-data.json"]:
            assessment = load(name)
            first = json.dumps(score.score(assessment, RUBRIC), sort_keys=False)
            second = json.dumps(score.score(assessment, RUBRIC), sort_keys=False)
            third = json.dumps(score.score(json.loads(json.dumps(assessment)), score.load_rubric()), sort_keys=False)
            self.assertEqual(first, second, f"{name}: two calls in the same process diverged")
            self.assertEqual(first, third, f"{name}: reloading rubric+re-serializing input changed output")

    def test_rubric_version_mismatch_raises(self):
        assessment = load("scored-strong.json")
        assessment["rubric_version"] = "999.0"
        with self.assertRaises(score.RubricVersionMismatch):
            score.score(assessment, RUBRIC)


class GateTests(unittest.TestCase):
    def test_strong_repo_all_gates_pass(self):
        result = score.score(load("scored-strong.json"), RUBRIC)
        self.assertTrue(result["gates_all_passed"])
        for gate in result["gates"]:
            self.assertTrue(gate["passed"], gate)
            self.assertIsNone(gate["remediation"])

    def test_sparse_legacy_fails_build_test_ci_gates(self):
        result = score.score(load("scored-sparse-legacy.json"), RUBRIC)
        failing = {g["id"] for g in result["gates"] if not g["passed"]}
        self.assertIn("GATE_BUILD", failing)
        self.assertIn("GATE_TEST_SIGNAL", failing)
        self.assertIn("GATE_CI", failing)
        self.assertFalse(result["gates_all_passed"])
        for gate in result["gates"]:
            if gate["id"] in failing:
                self.assertIsNotNone(gate["remediation"])

    def test_only_layer1_fails_gates_that_cannot_be_verified(self):
        result = score.score(load("scored-only-layer1.json"), RUBRIC)
        failing = {g["id"] for g in result["gates"] if not g["passed"]}
        # build/test/ci probes aren't implemented in this fixture -> unavailable -> must fail, not pass-by-default
        self.assertIn("GATE_BUILD", failing)
        self.assertIn("GATE_TEST_SIGNAL", failing)
        self.assertIn("GATE_CI", failing)
        # git history *is* available in this fixture -> GATE_VCS must pass
        vcs_gate = next(g for g in result["gates"] if g["id"] == "GATE_VCS")
        self.assertTrue(vcs_gate["passed"])


class DimensionBandTests(unittest.TestCase):
    def test_strong_repo_every_dimension_scores_100(self):
        result = score.score(load("scored-strong.json"), RUBRIC)
        for dim in result["dimensions"]:
            self.assertTrue(dim["available"], dim)
            self.assertEqual(dim["sub_score"], 100, dim)
        self.assertEqual(result["weighted_score"], 100.0)

    def test_low_parser_coverage_makes_structural_family_unavailable(self):
        result = score.score(load("scored-sparse-legacy.json"), RUBRIC)
        structural = next(d for d in result["dimensions"] if d["id"] == "structural_modularity")
        self.assertFalse(structural["available"])
        analyzability = next(d for d in result["dimensions"] if d["id"] == "analyzability")
        # parser_coverage_pct itself is still measured (35%), just below the
        # structural_modularity usability threshold — analyzability uses the
        # raw value directly and should still be available.
        self.assertTrue(analyzability["available"])
        self.assertEqual(analyzability["sub_score"], 15)  # band: >=20 -> 15... 35>=20 so 15? check band table
        # 35 >= 20 -> band "15"; confirm exact band edges below in a dedicated test.

    def test_debt_containability_band_edges(self):
        for value, expected in [(3, 100), (15, 70), (45, 40), (100, 15), (200, 0)]:
            doc = load("scored-strong.json")
            doc["metrics"]["debt.violations_per_kloc"]["value"] = value
            outcome = score.score_debt_containability(doc, RUBRIC)
            self.assertEqual(outcome[0], expected, f"violations_per_kloc={value}")

    def test_analyzability_band_edges(self):
        for value, expected in [(95, 100), (75, 70), (55, 40), (25, 15), (5, 0)]:
            doc = load("scored-strong.json")
            doc["metrics"]["structure.parser_coverage_pct"]["value"] = value
            outcome = score.score_analyzability(doc, RUBRIC)
            self.assertEqual(outcome[0], expected, f"parser_coverage_pct={value}")


class RedistributionTests(unittest.TestCase):
    def test_weight_redistributes_away_from_unavailable_dimension(self):
        result = score.score(load("scored-redistribution.json"), RUBRIC)
        debt_dim = next(d for d in result["dimensions"] if d["id"] == "debt_containability")
        self.assertFalse(debt_dim["available"])

        available = [d for d in result["dimensions"] if d["available"]]
        total_weight = sum(d["weight"] for d in available)
        self.assertEqual(total_weight, 100 - 8)  # debt_containability's weight (8) excluded

        expected = round(sum(d["weight"] * d["sub_score"] for d in available) / total_weight, 2)
        self.assertEqual(result["weighted_score"], expected)
        # every other dimension in this fixture is the strong-repo's perfect
        # 100, so the redistributed score should still land at 100.
        self.assertEqual(result["weighted_score"], 100.0)

    def test_only_layer1_has_no_available_dimensions(self):
        result = score.score(load("scored-only-layer1.json"), RUBRIC)
        self.assertEqual(result["weighted_score"], None)
        self.assertEqual(result["total_available_weight"], 0)
        for dim in result["dimensions"]:
            self.assertFalse(dim["available"], dim)


class VerdictTests(unittest.TestCase):
    def test_strong_repo_onboard_now(self):
        result = score.score(load("scored-strong.json"), RUBRIC)
        self.assertEqual(result["verdict"], "ONBOARD_NOW")
        self.assertEqual(result["recommended_starting_trust_level"], "L1")
        self.assertEqual(result["evidence_gate_to_advance"], ">80% PR acceptance over 20 PRs")
        self.assertFalse(result["do_not_onboard_override_applied"])

    def test_sparse_legacy_onboard_after_remediation_capped_by_gates(self):
        result = score.score(load("scored-sparse-legacy.json"), RUBRIC)
        self.assertEqual(result["verdict"], "ONBOARD_AFTER_REMEDIATION")
        self.assertEqual(result["recommended_starting_trust_level"], "L0")
        self.assertIsNone(result["evidence_gate_to_advance"])

    def test_do_not_onboard_overrides_high_score(self):
        result = score.score(load("scored-do-not-onboard.json"), RUBRIC)
        self.assertEqual(result["verdict"], "DO_NOT_ONBOARD")
        self.assertTrue(result["do_not_onboard_override_applied"])
        self.assertIsNone(result["recommended_starting_trust_level"])
        # weighted_score is still computed and reported for transparency, even
        # though the verdict overrides it outright. It's 85, not 100, because
        # roadmap_demand_next_2q="none" (what triggers the override) is the
        # SAME field change_demand's own sub-score reads — setting it to
        # "none" correctly drops change_demand's 15-weight contribution to 0
        # alongside triggering the override. That's real interaction, not a
        # fixture bug: DO_NOT_ONBOARD wins regardless of what the score is.
        self.assertEqual(result["weighted_score"], 85.0)

    def test_defer_when_gates_pass_but_score_low_and_demand_heavy(self):
        result = score.score(load("scored-defer.json"), RUBRIC)
        self.assertTrue(result["gates_all_passed"])
        self.assertLess(result["weighted_score"], RUBRIC["thresholds"]["onboard_after_remediation_min_score"])
        self.assertEqual(result["verdict"], "DEFER")

    def test_insufficient_data_note_when_gates_pass_but_no_dimension_scores(self):
        result = score.score(load("scored-gates-pass-no-data.json"), RUBRIC)
        self.assertTrue(result["gates_all_passed"], result["gates"])
        self.assertIsNone(result["weighted_score"])
        self.assertEqual(result["verdict"], "ONBOARD_AFTER_REMEDIATION")
        self.assertIn("no dimension had enough data", result["verdict_reason"])


if __name__ == "__main__":
    unittest.main()
