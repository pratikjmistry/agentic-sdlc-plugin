#!/usr/bin/env python3
"""Fixture- and tmp-dir-based tests for extract_facts.py: determinism, fact
mapping, file recommendations, DB/ORM detection, degraded-mode safety, and
the git-status reconciliation helper.

Run: python3 -m unittest discover -s scripts/tests -v
(or: cd scripts && python3 -m unittest tests.test_extract_facts -v)
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import extract_facts as ef  # noqa: E402

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


def load_zones() -> list[dict]:
    return json.loads((FIXTURES_DIR / "zones-sample.json").read_text())


class DeterminismTests(unittest.TestCase):
    def test_byte_identical_across_repeated_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            assessment_dir = Path(tmp) / "assessment"
            repo_dir = Path(tmp) / "repo"
            assessment_dir.mkdir()
            repo_dir.mkdir()
            (assessment_dir / "assessment-inputs.json").write_text(
                json.dumps(load("assessment-inputs-rich-signal.json")))
            (assessment_dir / "zones.json").write_text(json.dumps(load_zones()))

            first = json.dumps(ef.build_facts(assessment_dir, repo_dir), sort_keys=True)
            second = json.dumps(ef.build_facts(assessment_dir, repo_dir), sort_keys=True)
            self.assertEqual(first, second)

    def test_missing_assessment_inputs_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                ef.build_facts(Path(tmp), Path(tmp))

    def test_missing_zones_json_yields_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            assessment_dir = Path(tmp)
            (assessment_dir / "assessment-inputs.json").write_text(
                json.dumps(load("assessment-inputs-rich-signal.json")))
            self.assertEqual(ef.load_zones(assessment_dir), [])


class FactMappingTests(unittest.TestCase):
    def setUp(self):
        self.inputs = load("assessment-inputs-rich-signal.json")
        self.zones = load_zones()

    def test_tech_stack_facts_pull_documented_metrics(self):
        facts = ef.build_tech_stack_facts(self.inputs)
        for mid in ef.TECH_STACK_METRICS:
            self.assertIn(mid, facts["metrics"], mid)

    def test_testing_facts_pull_full_test_family(self):
        facts = ef.build_testing_facts(self.inputs)
        for mid in ef.TESTING_METRICS:
            self.assertIn(mid, facts["metrics"], mid)

    def test_security_facts_always_state_no_auth_signal(self):
        facts = ef.build_security_facts(self.inputs)
        self.assertIn("no auth/authz signal", facts["notes"])

    def test_architecture_facts_include_monorepo_and_zones(self):
        facts = ef.build_architecture_facts(self.inputs, self.zones, {})
        self.assertTrue(facts["is_monorepo"])
        self.assertEqual(len(facts["detected_projects"]), 2)
        self.assertEqual(facts["zones"], self.zones)

    def test_database_guidelines_facts_include_db_orm(self):
        db_orm = ef.detect_db_orm(Path("/nonexistent-path-for-test"))
        facts = ef.build_database_guidelines_facts(self.inputs, db_orm)
        self.assertEqual(facts["db_orm"], db_orm)


class RecommendationTests(unittest.TestCase):
    def test_security_and_ralph_spec_always_recommended(self):
        inputs = load("assessment-inputs-sparse-legacy.json")
        recs = ef.recommend_files(inputs, {"present": False})
        self.assertTrue(recs["security.md"]["recommend"])
        self.assertTrue(recs["ralph-agent-spec.md"]["recommend"])

    def test_api_guidelines_follows_api_spec_signal(self):
        inputs = load("assessment-inputs-rich-signal.json")
        recs_present = ef.recommend_files(inputs, {"present": False})
        self.assertTrue(recs_present["api-guidelines.md"]["recommend"])

        inputs["metrics"]["context.api_spec_present"]["value"] = False
        recs_absent = ef.recommend_files(inputs, {"present": False})
        self.assertFalse(recs_absent["api-guidelines.md"]["recommend"])

    def test_design_system_follows_frontend_language_share(self):
        inputs = load("assessment-inputs-rich-signal.json")
        recs = ef.recommend_files(inputs, {"present": False})
        # rich-signal fixture: TypeScript 33% + CSS 12% = 45% frontend share
        self.assertTrue(recs["design-system.md"]["recommend"])

        inputs2 = load("assessment-inputs-sparse-legacy.json")
        recs2 = ef.recommend_files(inputs2, {"present": False})
        self.assertFalse(recs2["design-system.md"]["recommend"])

    def test_database_guidelines_follows_db_orm_presence(self):
        inputs = load("assessment-inputs-sparse-legacy.json")
        recs_no_orm = ef.recommend_files(inputs, {"present": False})
        self.assertFalse(recs_no_orm["database-guidelines.md"]["recommend"])

        recs_with_orm = ef.recommend_files(inputs, {"present": True})
        self.assertTrue(recs_with_orm["database-guidelines.md"]["recommend"])

    def test_repo_structure_follows_monorepo_signal(self):
        inputs = load("assessment-inputs-rich-signal.json")
        recs = ef.recommend_files(inputs, {"present": False})
        self.assertTrue(recs["repo-structure.md"]["recommend"])


class DbOrmDetectionTests(unittest.TestCase):
    def test_no_markers_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = ef.detect_db_orm(Path(tmp))
            self.assertFalse(result["present"])
            self.assertEqual(result["evidence"], [])

    def test_alembic_marker_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "alembic.ini").write_text("[alembic]\n")
            result = ef.detect_db_orm(Path(tmp))
            self.assertTrue(result["present"])
            self.assertIn("alembic.ini", result["evidence"])

    def test_migrations_directory_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "migrations").mkdir()
            result = ef.detect_db_orm(Path(tmp))
            self.assertTrue(result["present"])
            self.assertIn("migrations/ directory", result["evidence"])

    def test_codeowners_found_and_parsed(self):
        with tempfile.TemporaryDirectory() as tmp:
            github_dir = Path(tmp) / ".github"
            github_dir.mkdir()
            (github_dir / "CODEOWNERS").write_text("* @org/platform-team\n/docs/ @alice\n")
            result = ef.detect_codeowners(Path(tmp))
            self.assertTrue(result["present"])
            self.assertEqual(result["path"], ".github/CODEOWNERS")
            self.assertIn("@org/platform-team", result["owners_sample"])
            self.assertIn("@alice", result["owners_sample"])

    def test_codeowners_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = ef.detect_codeowners(Path(tmp))
            self.assertFalse(result["present"])


class DegradedModeTests(unittest.TestCase):
    def test_sparse_legacy_never_crashes_and_flags_unavailable(self):
        inputs = load("assessment-inputs-sparse-legacy.json")
        arch_facts = ef.build_architecture_facts(inputs, [], {})
        self.assertEqual(arch_facts["risk_areas"], [])
        self.assertEqual(arch_facts["metrics"]["structure.god_nodes"]["confidence"], "unavailable")

    def test_missing_map_codebase_outputs_reported_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            outputs = ef.find_map_codebase_outputs(Path(tmp))
            self.assertFalse(outputs["codebase_map_present"])
            self.assertFalse(outputs["graphify_analysis_present"])
            self.assertIsNone(outputs["codebase_map_path"])


class ReconciliationHelperTests(unittest.TestCase):
    def _init_repo(self, path: Path) -> None:
        subprocess.run(["git", "init", "-q", str(path)], check=True)
        subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"], check=True)

    def test_no_git_repo_is_not_reconcilable(self):
        with tempfile.TemporaryDirectory() as tmp:
            reconcilable, detail = ef.ai_context_is_reconcilable(Path(tmp))
            self.assertFalse(reconcilable)
            self.assertIn("not a git repository", detail)

    def test_clean_ai_context_is_reconcilable(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._init_repo(repo)
            ai_context = repo / "ai-context"
            ai_context.mkdir()
            (ai_context / "architecture.md").write_text("# Architecture\n")
            subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "init"], check=True)

            reconcilable, detail = ef.ai_context_is_reconcilable(repo)
            self.assertTrue(reconcilable, detail)

    def test_dirty_ai_context_is_not_reconcilable(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._init_repo(repo)
            ai_context = repo / "ai-context"
            ai_context.mkdir()
            (ai_context / "architecture.md").write_text("# Architecture\n")
            subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "init"], check=True)
            (ai_context / "architecture.md").write_text("# Architecture (locally edited)\n")

            reconcilable, detail = ef.ai_context_is_reconcilable(repo)
            self.assertFalse(reconcilable)
            self.assertIn("uncommitted changes", detail)

    def test_untracked_ai_context_is_not_reconcilable(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._init_repo(repo)
            ai_context = repo / "ai-context"
            ai_context.mkdir()
            (ai_context / "architecture.md").write_text("# Architecture\n")
            # never git-added — untracked

            reconcilable, detail = ef.ai_context_is_reconcilable(repo)
            self.assertFalse(reconcilable)


class RiskAreaTests(unittest.TestCase):
    def test_god_nodes_and_cycles_and_wide_zones_all_surface(self):
        inputs = load("assessment-inputs-rich-signal.json")
        zones = load_zones()
        facts = ef.build_architecture_facts(inputs, zones, {})
        kinds = {ra["kind"] for ra in facts["risk_areas"]}
        self.assertIn("god_node", kinds)
        self.assertIn("cyclic_dependencies", kinds)
        self.assertIn("zone_blast_radius", kinds)

        god_node_entries = [ra for ra in facts["risk_areas"] if ra["kind"] == "god_node"]
        # sorted by fan_in+fan_out descending: EngineCore (40+22=62) before Utils (55+3=58)
        self.assertEqual(god_node_entries[0]["identifier"], "EngineCore")

        for ra in facts["risk_areas"]:
            self.assertIn("/plan-seams", ra["why"])

    def test_empty_when_structure_family_unavailable(self):
        inputs = load("assessment-inputs-sparse-legacy.json")
        facts = ef.build_architecture_facts(inputs, [], {})
        self.assertEqual(facts["risk_areas"], [])

    def test_contained_zone_never_flagged(self):
        inputs = load("assessment-inputs-rich-signal.json")
        zones = load_zones()
        facts = ef.build_architecture_facts(inputs, zones, {})
        identifiers = {ra["identifier"] for ra in facts["risk_areas"] if ra["kind"] == "zone_blast_radius"}
        self.assertIn("src/core", identifiers)
        self.assertNotIn("src/util", identifiers)  # contained, low coupling — should not appear


if __name__ == "__main__":
    unittest.main()
