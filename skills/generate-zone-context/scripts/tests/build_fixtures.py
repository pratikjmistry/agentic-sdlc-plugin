#!/usr/bin/env python3
"""Generates the fixtures under tests/fixtures/ used by test_extract_zone_facts.py.
Run this to regenerate fixtures after changing what extract_zone_facts.py reads;
the fixtures themselves are committed, this script is not invoked at test time.

Two zones (ZONE-01 = src/core, ZONE-02 = src/util) with graph data engineered
so each zone's community/hub/surprise data is disjoint from the other's — this
is what ZoneFilteringTests checks for "no cross-contamination between zones."
"""
from __future__ import annotations

import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

ZONES = [
    {
        "id": "ZONE-01", "name": "src/core", "paths": ["src/core/engine.py"], "stack": ["py"],
        "loc": 800, "coverage_pct": None, "churn_rank": 1,
        "coupling_score": 0.72, "blast_radius": "wide",
        "recommended_trust_level": "L0", "blockers": ["GATE_TEST_SIGNAL"],
        "rationale": "Highest combined churn x size in this pass.",
    },
    {
        "id": "ZONE-02", "name": "src/util", "paths": ["src/util.py"], "stack": ["py"],
        "loc": 200, "coverage_pct": None, "churn_rank": 2,
        "coupling_score": 0.10, "blast_radius": "contained",
        "recommended_trust_level": "L1", "blockers": [],
        "rationale": "Second-highest combined churn x size in this pass.",
    },
]

GRAPH = {
    "directed": True,
    "multigraph": False,
    "nodes": [
        {"id": "n1", "label": "engine.py", "file_type": "file", "source_file": "src/core/engine.py", "community": "0"},
        {"id": "n2", "label": "EngineCore", "file_type": "function", "source_file": "src/core/engine.py", "community": "0"},
        {"id": "n3", "label": "util.py", "file_type": "file", "source_file": "src/util.py", "community": "1"},
        {"id": "n4", "label": "Utils", "file_type": "function", "source_file": "src/util.py", "community": "1"},
        {"id": "n5", "label": "outside.py", "file_type": "file", "source_file": "src/other/outside.py", "community": "2"},
    ],
    "links": [
        {"source": "n2", "target": "n4", "relation": "calls", "source_file": "src/core/engine.py"},
        {"source": "n4", "target": "n5", "relation": "calls", "source_file": "src/util.py"},
    ],
}

GRAPHIFY_ANALYSIS = {
    "communities": {"0": ["n1", "n2"], "1": ["n3", "n4"], "2": ["n5"]},
    "cohesion": {"0": 0.8, "1": 0.6, "2": 1.0},
    "gods": [
        {"id": "n2", "label": "EngineCore", "degree": 5},
        {"id": "n4", "label": "Utils", "degree": 3},
    ],
    "surprises": [
        {"source": "n2", "target": "n4", "source_files": ["src/core/engine.py"],
         "confidence": 0.9, "relation": "calls", "why": "cross-community dependency"},
        {"source": "n4", "target": "n5", "source_files": ["src/util.py"],
         "confidence": 0.7, "relation": "calls", "why": "cross-community dependency"},
    ],
    "questions": [],
    "tokens": {"input": 0, "output": 0},
}

CONSTITUTION_FACTS = {
    "facts": {
        "architecture": {
            "risk_areas": [
                {"kind": "zone_blast_radius", "identifier": "src/core",
                 "detail": "blast_radius=wide, coupling_score=0.72, churn_rank=1",
                 "why": ("Wide blast radius plus high churn — prioritize a characterization test here "
                         "before /plan-seams proposes a seam."),
                 "confidence": "derived"},
                {"kind": "god_node", "identifier": "EngineCore",
                 "detail": "fan_in=40, fan_out=22 at src/core/engine.py",
                 "why": "High-coupling hub — a seam candidate for /plan-seams.",
                 "confidence": "derived"},
            ],
        },
    },
}


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    fixtures = {
        "zones-sample.json": ZONES,
        "graph-sample.json": GRAPH,
        "graphify-analysis-sample.json": GRAPHIFY_ANALYSIS,
        "constitution-facts-sample.json": CONSTITUTION_FACTS,
    }
    for filename, doc in fixtures.items():
        path = FIXTURES_DIR / filename
        path.write_text(json.dumps(doc, indent=2) + "\n")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
