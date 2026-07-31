#!/usr/bin/env python3
"""Fixture- and tmp-dir-based tests for extract_zone_facts.py: determinism,
per-zone filtering with no cross-contamination, slugification, degraded-mode
safety, risk-area cross-referencing, and the ai-context/zones/ git-status
reconciliation helper.

Run: python3 -m unittest discover -s scripts/tests -v
(or: cd scripts && python3 -m unittest tests.test_extract_zone_facts -v)
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

import extract_zone_facts as ezf  # noqa: E402

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def load(name: str):
    return json.loads((FIXTURES_DIR / name).read_text())


def _write_graphify_out(repo_dir: Path) -> None:
    graphify_out = repo_dir / "graphify-out"
    graphify_out.mkdir(parents=True, exist_ok=True)
    (graphify_out / "graph.json").write_text(json.dumps(load("graph-sample.json")))
    (graphify_out / ".graphify_analysis.json").write_text(json.dumps(load("graphify-analysis-sample.json")))


def _write_assessment(assessment_dir: Path, with_constitution_facts: bool = False) -> None:
    assessment_dir.mkdir(parents=True, exist_ok=True)
    (assessment_dir / "zones.json").write_text(json.dumps(load("zones-sample.json")))
    if with_constitution_facts:
        (assessment_dir / "constitution-facts.json").write_text(json.dumps(load("constitution-facts-sample.json")))


class DeterminismTests(unittest.TestCase):
    def test_byte_identical_across_repeated_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            assessment_dir = Path(tmp) / "assessment"
            repo_dir = Path(tmp) / "repo"
            _write_assessment(assessment_dir, with_constitution_facts=True)
            repo_dir.mkdir()
            _write_graphify_out(repo_dir)

            first = json.dumps(ezf.build_all_zone_facts(assessment_dir, repo_dir), sort_keys=True)
            second = json.dumps(ezf.build_all_zone_facts(assessment_dir, repo_dir), sort_keys=True)
            self.assertEqual(first, second)

    def test_missing_zones_json_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                ezf.load_zones(Path(tmp))

    def test_empty_zones_json_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            assessment_dir = Path(tmp)
            (assessment_dir / "zones.json").write_text("[]")
            with self.assertRaises(ValueError):
                ezf.load_zones(assessment_dir)

    def test_missing_constitution_facts_yields_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(ezf.load_constitution_facts(Path(tmp)))


class ZoneFilteringTests(unittest.TestCase):
    def setUp(self):
        self.zones = load("zones-sample.json")
        self.graph = load("graph-sample.json")
        self.analysis = load("graphify-analysis-sample.json")
        self.zone_core = self.zones[0]
        self.zone_util = self.zones[1]

    def test_no_cross_contamination_between_zones(self):
        core_facts = ezf.build_zone_facts(self.zone_core, self.graph, self.analysis, None)
        util_facts = ezf.build_zone_facts(self.zone_util, self.graph, self.analysis, None)

        core_hub_labels = {h["label"] for h in core_facts["hubs"]}
        util_hub_labels = {h["label"] for h in util_facts["hubs"]}
        self.assertEqual(core_hub_labels, {"EngineCore"})
        self.assertEqual(util_hub_labels, {"Utils"})
        self.assertTrue(core_hub_labels.isdisjoint(util_hub_labels))

    def test_communities_filtered_by_overlap(self):
        core_facts = ezf.build_zone_facts(self.zone_core, self.graph, self.analysis, None)
        self.assertEqual(len(core_facts["communities"]), 1)
        self.assertEqual(core_facts["communities"][0]["id"], "0")
        self.assertEqual(core_facts["communities"][0]["overlap_count"], 2)

    def test_surprises_filtered_by_zone_paths(self):
        core_facts = ezf.build_zone_facts(self.zone_core, self.graph, self.analysis, None)
        util_facts = ezf.build_zone_facts(self.zone_util, self.graph, self.analysis, None)
        self.assertEqual(len(core_facts["surprises"]), 1)
        self.assertEqual(core_facts["surprises"][0]["source_files"], ["src/core/engine.py"])
        self.assertEqual(len(util_facts["surprises"]), 1)
        self.assertEqual(util_facts["surprises"][0]["source_files"], ["src/util.py"])

    def test_output_filename_uses_zone_id_and_slug(self):
        core_facts = ezf.build_zone_facts(self.zone_core, self.graph, self.analysis, None)
        self.assertEqual(core_facts["output_filename"], "ZONE-01-src-core.md")

    def test_rule_output_path_uses_same_id_and_slug_under_claude_rules_zones(self):
        core_facts = ezf.build_zone_facts(self.zone_core, self.graph, self.analysis, None)
        self.assertEqual(core_facts["rule_output_path"], ".claude/rules/zones/ZONE-01-src-core.md")

    def test_rule_output_path_handles_single_file_zone_name(self):
        # Real case seen in this session's own Flask dry run: a zone's `name`
        # can be a single file, not a directory (e.g. "tests/test_basic.py").
        # rule_output_path must still be well-formed — it never assumes
        # zone.name is a directory the way a `<name>/**` glob heuristic would.
        single_file_zone = {
            "id": "ZONE-02", "name": "tests/test_basic.py", "paths": ["tests/test_basic.py"],
        }
        facts = ezf.build_zone_facts(single_file_zone, None, None, None)
        self.assertEqual(facts["rule_output_path"], ".claude/rules/zones/ZONE-02-tests-test_basic-py.md")


class SlugTests(unittest.TestCase):
    def test_simple_path(self):
        self.assertEqual(ezf.slugify_zone_name("src/core"), "src-core")

    def test_distinct_names_do_not_collide(self):
        self.assertNotEqual(ezf.slugify_zone_name("src/core"), ezf.slugify_zone_name("lib/core"))

    def test_uppercase_and_special_chars(self):
        self.assertEqual(ezf.slugify_zone_name("Src/Core Module!!"), "src-core-module")

    def test_empty_name_falls_back(self):
        self.assertEqual(ezf.slugify_zone_name(""), "zone")
        self.assertEqual(ezf.slugify_zone_name(None), "zone")


class DegradedModeTests(unittest.TestCase):
    def test_missing_graph_yields_empty_lists_and_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            zone = load("zones-sample.json")[0]
            result = ezf.build_zone_facts(zone, None, None, None)
            self.assertFalse(result["map_codebase_available"])
            self.assertEqual(result["communities"], [])
            self.assertEqual(result["hubs"], [])
            self.assertEqual(result["surprises"], [])

    def test_load_graph_returns_none_when_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(ezf.load_graph(Path(tmp)))

    def test_build_all_zone_facts_never_crashes_without_map_codebase_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            assessment_dir = Path(tmp) / "assessment"
            repo_dir = Path(tmp) / "repo"
            _write_assessment(assessment_dir)
            repo_dir.mkdir()
            result = ezf.build_all_zone_facts(assessment_dir, repo_dir)
            self.assertFalse(result["map_codebase_outputs"]["graph_json_present"])
            for zone_bundle in result["zones"]:
                self.assertFalse(zone_bundle["map_codebase_available"])


class CrossReferenceTests(unittest.TestCase):
    def test_none_constitution_facts_yields_empty_list(self):
        zone = load("zones-sample.json")[0]
        self.assertEqual(ezf.cross_reference_risk_areas(zone, None), [])

    def test_matches_by_name(self):
        zone = load("zones-sample.json")[0]  # name == "src/core"
        facts = load("constitution-facts-sample.json")
        matches = ezf.cross_reference_risk_areas(zone, facts)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["identifier"], "src/core")

    def test_non_matching_zone_yields_empty_list(self):
        zone = load("zones-sample.json")[1]  # name == "src/util", no matching risk_area
        facts = load("constitution-facts-sample.json")
        self.assertEqual(ezf.cross_reference_risk_areas(zone, facts), [])

    def test_god_node_kind_never_matched(self):
        # constitution-facts-sample.json also has a "god_node" kind entry with
        # identifier "EngineCore" — must never be returned regardless of zone.
        zone = {"id": "ZONE-EngineCore", "name": "EngineCore"}
        facts = load("constitution-facts-sample.json")
        self.assertEqual(ezf.cross_reference_risk_areas(zone, facts), [])


class ReconciliationHelperTests(unittest.TestCase):
    def _init_repo(self, path: Path) -> None:
        subprocess.run(["git", "init", "-q", str(path)], check=True)
        subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"], check=True)

    def test_no_git_repo_is_not_reconcilable(self):
        with tempfile.TemporaryDirectory() as tmp:
            reconcilable, detail = ezf.zones_dir_is_reconcilable(Path(tmp))
            self.assertFalse(reconcilable)
            self.assertIn("not a git repository", detail)

    def test_clean_zones_dir_is_reconcilable(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._init_repo(repo)
            zones_dir = repo / "ai-context" / "zones"
            zones_dir.mkdir(parents=True)
            (zones_dir / "ZONE-01-src-core.md").write_text("# Zone\n")
            subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "init"], check=True)

            reconcilable, detail = ezf.zones_dir_is_reconcilable(repo)
            self.assertTrue(reconcilable, detail)

    def test_dirty_zones_dir_is_not_reconcilable(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._init_repo(repo)
            zones_dir = repo / "ai-context" / "zones"
            zones_dir.mkdir(parents=True)
            (zones_dir / "ZONE-01-src-core.md").write_text("# Zone\n")
            subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "init"], check=True)
            (zones_dir / "ZONE-01-src-core.md").write_text("# Zone (locally edited)\n")

            reconcilable, detail = ezf.zones_dir_is_reconcilable(repo)
            self.assertFalse(reconcilable)
            self.assertIn("uncommitted changes", detail)

    def test_dirty_ai_context_but_clean_zones_dir_is_still_reconcilable(self):
        """A dirty architecture.md elsewhere in ai-context/ must not block
        zone-file generation — the pathspec is scoped to ai-context/zones/."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._init_repo(repo)
            ai_context = repo / "ai-context"
            zones_dir = ai_context / "zones"
            zones_dir.mkdir(parents=True)
            (zones_dir / "ZONE-01-src-core.md").write_text("# Zone\n")
            (ai_context / "architecture.md").write_text("# Architecture\n")
            subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "init"], check=True)
            (ai_context / "architecture.md").write_text("# Architecture (locally edited)\n")

            reconcilable, detail = ezf.zones_dir_is_reconcilable(repo)
            self.assertTrue(reconcilable, detail)

    def test_dirty_rules_zones_does_not_block_clean_ai_context_zones(self):
        """The two reconciliation checks are independent: a dirty
        .claude/rules/zones/ must not affect ai-context/zones/'s own verdict."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._init_repo(repo)
            ai_zones = repo / "ai-context" / "zones"
            rule_zones = repo / ".claude" / "rules" / "zones"
            ai_zones.mkdir(parents=True)
            rule_zones.mkdir(parents=True)
            (ai_zones / "ZONE-01-src-core.md").write_text("# Zone\n")
            (rule_zones / "ZONE-01-src-core.md").write_text("---\npaths: []\n---\n")
            subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "init"], check=True)
            (rule_zones / "ZONE-01-src-core.md").write_text("---\npaths: [\"edited\"]\n---\n")

            ai_context_reconcilable, _ = ezf.zones_dir_is_reconcilable(repo)
            rules_reconcilable, rules_detail = ezf.rules_dir_is_reconcilable(repo)
            self.assertTrue(ai_context_reconcilable)
            self.assertFalse(rules_reconcilable)
            self.assertIn("uncommitted changes", rules_detail)

    def test_dirty_ai_context_zones_does_not_block_clean_rules_zones(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._init_repo(repo)
            ai_zones = repo / "ai-context" / "zones"
            rule_zones = repo / ".claude" / "rules" / "zones"
            ai_zones.mkdir(parents=True)
            rule_zones.mkdir(parents=True)
            (ai_zones / "ZONE-01-src-core.md").write_text("# Zone\n")
            (rule_zones / "ZONE-01-src-core.md").write_text("---\npaths: []\n---\n")
            subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "init"], check=True)
            (ai_zones / "ZONE-01-src-core.md").write_text("# Zone (locally edited)\n")

            ai_context_reconcilable, _ = ezf.zones_dir_is_reconcilable(repo)
            rules_reconcilable, _ = ezf.rules_dir_is_reconcilable(repo)
            self.assertFalse(ai_context_reconcilable)
            self.assertTrue(rules_reconcilable)


class BuildAllZoneFactsReconciliationTests(unittest.TestCase):
    def test_reconciliation_has_both_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            assessment_dir = Path(tmp) / "assessment"
            repo_dir = Path(tmp) / "repo"
            _write_assessment(assessment_dir)
            repo_dir.mkdir()
            result = ezf.build_all_zone_facts(assessment_dir, repo_dir)
            self.assertIn("ai_context_zones", result["reconciliation"])
            self.assertIn("rules_zones", result["reconciliation"])
            self.assertIn("reconcilable", result["reconciliation"]["ai_context_zones"])
            self.assertIn("reconcilable", result["reconciliation"]["rules_zones"])


if __name__ == "__main__":
    unittest.main()
