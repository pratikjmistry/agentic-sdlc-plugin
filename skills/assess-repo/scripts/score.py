#!/usr/bin/env python3
"""Pure scoring function for /assess-repo. NO model calls, NO network access,
NO wall-clock or random calls anywhere in this module — every field in its
output is a deterministic function of (assessment-inputs.json, rubric.yaml).
That is what "same commit + same rubric version -> byte-identical scores"
requires, and it's why this file has no `datetime.now()` of its own: it only
ever echoes timestamps that were already in the input document.

One dependency beyond the stdlib: PyYAML, to parse rubric.yaml. This was a
deliberate, documented scope call (not an oversight) — rubric.yaml is meant to
stay human-readable with real comments for the "review the banding" use case
this skill exists for, and PyYAML is a near-universal, lightweight package.
If this call should instead be zero-dependency (matching validate.py's
jsonschema-with-fallback pattern), say so and a bundled minimal parser for
this rubric's specific shape can replace it.

Usage:
    python3 score.py <assessment-inputs.json> [--rubric PATH] [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only in envs without PyYAML
    print(
        "score.py requires PyYAML to parse rubric.yaml. Install it with "
        "`pip install pyyaml` (or `uv pip install pyyaml`). This is score.py's "
        "one dependency beyond the standard library.",
        file=sys.stderr,
    )
    raise

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_RUBRIC_PATH = SCRIPT_DIR.parent / "assets" / "rubric.yaml"


class RubricVersionMismatch(Exception):
    pass


def load_rubric(path: Path = DEFAULT_RUBRIC_PATH) -> dict:
    return yaml.safe_load(Path(path).read_text())


def _metric(assessment: dict, metric_id: str) -> dict:
    return assessment["metrics"][metric_id]


def _available(assessment: dict, metric_id: str) -> bool:
    return _metric(assessment, metric_id)["confidence"] != "unavailable"


def _value(assessment: dict, metric_id: str):
    return _metric(assessment, metric_id)["value"]


def _human(assessment: dict, key: str):
    return assessment.get("human_inputs", {}).get(key)


# ---------------------------------------------------------------------------
# Hard gates
# ---------------------------------------------------------------------------

def _gate_vcs(assessment: dict) -> tuple[bool, str]:
    target = assessment["target"]
    if target["mode"] == "local_path" and not target["resolved_commit"]:
        return False, "target is not a git repository (no resolved commit)"
    if not target["default_branch"]:
        return False, "no default branch could be identified"
    return True, "git history accessible, default branch identified"


def _gate_build(assessment: dict) -> tuple[bool, str]:
    signals = ["build.containerized", "build.devcontainer_present", "build.one_command_build_documented"]
    if not all(_available(assessment, m) for m in signals):
        return False, "build capability could not be determined (build_probe did not run, or its detection was inconclusive)"
    attempt = _value(assessment, "build.attempt")
    if attempt and attempt.get("attempted"):
        if attempt.get("exit_code") == 0:
            return True, "clean-clone build succeeded"
        return False, f"attempted build failed (exit code {attempt.get('exit_code')})"
    if any(_value(assessment, m) for m in signals):
        return True, "detect-only: a one-command build path is documented"
    return False, "no build system detected"


def _gate_test_signal(assessment: dict) -> tuple[bool, str]:
    if not _available(assessment, "test.suite_executes"):
        return False, ("test capability could not be verified — detect-only mode does not execute the "
                        "suite; re-run with --attempt-test (requires --attempt-build) for a real signal")
    if _value(assessment, "test.suite_executes"):
        return True, "test suite executes to a deterministic pass/fail result"
    return False, "no test suite executes"


def _gate_ci(assessment: dict) -> tuple[bool, str]:
    if not _available(assessment, "ci.systems_detected") or not _available(assessment, "ci.runs_on_pr"):
        return False, "CI capability could not be determined (ci_probe did not run, or its trigger config was unparseable)"
    if _value(assessment, "ci.runs_on_pr"):
        return True, "CI runs on pull request"
    return False, "no CI detected running on pull request"


def _gate_policy(assessment: dict) -> tuple[bool, str]:
    allowed = assessment.get("human_inputs", {}).get("client_data_policy", {}).get("third_party_tooling_allowed")
    if allowed is False:
        return False, "client data policy forbids third-party tooling this pathway requires"
    return True, "no policy restriction recorded, or tooling explicitly permitted"


GATE_FUNCTIONS = {
    "GATE_VCS": _gate_vcs,
    "GATE_BUILD": _gate_build,
    "GATE_TEST_SIGNAL": _gate_test_signal,
    "GATE_CI": _gate_ci,
    "GATE_POLICY": _gate_policy,
}


def evaluate_gates(assessment: dict, rubric: dict) -> list[dict]:
    results = []
    for gate_id, gate_def in rubric["hard_gates"].items():
        fn = GATE_FUNCTIONS[gate_id]
        passed, reason = fn(assessment)
        results.append({
            "id": gate_id,
            "description": gate_def["description"],
            "passed": passed,
            "reason": reason,
            "remediation": None if passed else gate_def["remediation"].strip(),
        })
    return results


# ---------------------------------------------------------------------------
# Weighted dimensions — one function per dimension, matching rubric.yaml's
# `bands` documentation for that dimension exactly. Each returns (score, reason)
# or None if the dimension is unavailable (a required backing metric is missing).
# ---------------------------------------------------------------------------

def _require(assessment: dict, metric_ids: list[str]) -> bool:
    return all(_available(assessment, m) for m in metric_ids)


def score_build_reproducibility(assessment: dict, rubric: dict) -> tuple[int, str] | None:
    ids = ["build.containerized", "build.devcontainer_present", "build.one_command_build_documented",
           "build.detected_systems", "build.lockfiles_present"]
    if not _require(assessment, ids):
        return None
    containerized = _value(assessment, "build.containerized")
    devcontainer = _value(assessment, "build.devcontainer_present")
    one_command = _value(assessment, "build.one_command_build_documented")
    detected = _value(assessment, "build.detected_systems") or []
    lockfiles = _value(assessment, "build.lockfiles_present")
    attempt = _value(assessment, "build.attempt") if _available(assessment, "build.attempt") else None

    if (containerized or devcontainer) and one_command:
        if attempt and attempt.get("attempted") and attempt.get("exit_code") != 0:
            return 50, "one-command/containerized build documented, but an attempted build failed"
        return 100, "containerized or devcontainer present, with a documented one-command build"
    if one_command:
        return 75, "one-command build documented (not containerized)"
    if lockfiles and detected:
        return 50, "build system identifiable and lockfiles present, but no one-command path documented"
    if detected:
        return 25, "build system identifiable only"
    return 0, "no build system detected"


def score_test_safety_net(assessment: dict, rubric: dict) -> tuple[int, str] | None:
    ids = ["test.suite_executes", "test.coverage_pct", "test.unit_present",
           "test.integration_present", "test.test_file_count"]
    if not _require(assessment, ids):
        return None
    executes = _value(assessment, "test.suite_executes")
    coverage = _value(assessment, "test.coverage_pct")
    unit = _value(assessment, "test.unit_present")
    integration = _value(assessment, "test.integration_present")
    test_files = _value(assessment, "test.test_file_count") or 0

    if executes and coverage is not None and coverage >= 70 and unit and integration:
        return 100, "suite executes, coverage >= 70%, unit and integration tests both present"
    if executes and coverage is not None and coverage >= 40:
        return 80, "suite executes, coverage >= 40%"
    if executes:
        return 60, "suite executes, coverage below 40% or unknown"
    if test_files > 0:
        return 30, "test files exist but the suite does not execute"
    return 0, "no test files detected"


def score_change_demand(assessment: dict, rubric: dict) -> tuple[int, str] | None:
    demand = _human(assessment, "roadmap_demand_next_2q")
    if demand is None:
        return None
    mapping = {"heavy": (100, "heavy roadmap demand"), "moderate": (70, "moderate roadmap demand"),
               "low": (30, "low roadmap demand"), "none": (0, "no roadmap demand")}
    return mapping.get(demand, (0, f"unrecognized roadmap_demand_next_2q value '{demand}'"))


def score_structural_modularity(assessment: dict, rubric: dict) -> tuple[int, str] | None:
    ids = ["structure.parser_coverage_pct", "structure.cyclic_dependency_count",
           "structure.god_nodes", "structure.avg_fan_out"]
    if not _require(assessment, ids):
        return None
    coverage = _value(assessment, "structure.parser_coverage_pct")
    min_coverage = rubric["thresholds"]["structure_parser_coverage_min_for_use"]
    if coverage is None or coverage < min_coverage:
        return None  # parser coverage too low to trust this family at all

    cycles = _value(assessment, "structure.cyclic_dependency_count") or 0
    god_nodes = _value(assessment, "structure.god_nodes") or []
    fan_out = _value(assessment, "structure.avg_fan_out") or 0

    if cycles == 0 and not god_nodes and fan_out <= 5:
        return 100, "no cycles, no god nodes, low average fan-out"
    if cycles <= 2 and fan_out <= 10:
        return 70, "few cycles, moderate fan-out"
    if cycles <= 10 or len(god_nodes) < 5:
        return 40, "some cycles or a handful of god nodes"
    if cycles > 10:
        return 15, "many cyclic dependencies or god nodes"
    return 0, "pervasive cycles or extreme fan-out"


def score_stack_coherence(assessment: dict, rubric: dict) -> tuple[int, str] | None:
    ids = ["codebase.distinct_stacks_count", "deps.duplicate_framework_versions", "deps.median_majors_behind"]
    if not _require(assessment, ids):
        return None
    stacks = _value(assessment, "codebase.distinct_stacks_count") or 0
    dupes = _value(assessment, "deps.duplicate_framework_versions") or []
    majors_behind = _value(assessment, "deps.median_majors_behind") or 0

    if stacks <= 2 and not dupes and majors_behind <= 1:
        return 100, "minimal stack fragmentation, no duplicate framework versions"
    if stacks <= 4 and not dupes:
        return 70, "modest stack count, no duplicate framework versions"
    if len(dupes) == 1 or 5 <= stacks <= 7:
        return 40, "one duplicate-version framework, or a wider stack spread"
    if len(dupes) > 1 or stacks > 7:
        return 15, "multiple duplicate-version frameworks or wide stack spread"
    return 0, "severe stack fragmentation"


def score_debt_containability(assessment: dict, rubric: dict) -> tuple[int, str] | None:
    ids = ["debt.violations_per_kloc", "debt.baselineable"]
    if not _require(assessment, ids):
        return None
    per_kloc = _value(assessment, "debt.violations_per_kloc") or 0
    baselineable = _value(assessment, "debt.baselineable")

    if per_kloc <= 5 and baselineable:
        return 100, "very low violation density, baselineable"
    if per_kloc <= 20 and baselineable:
        return 70, "low violation density, baselineable"
    if per_kloc <= 50:
        return 40, "moderate violation density"
    if per_kloc <= 150:
        return 15, "high violation density"
    return 0, "very high violation density or not baselineable"


def score_context_availability(assessment: dict, rubric: dict) -> tuple[int, str] | None:
    ids = ["context.readme_quality_score", "context.adr_count",
           "context.domain_glossary_present", "context.ai_context_present"]
    if not _require(assessment, ids):
        return None
    readme = _value(assessment, "context.readme_quality_score") or 0
    adrs = _value(assessment, "context.adr_count") or 0
    glossary = _value(assessment, "context.domain_glossary_present")
    ai_context = _value(assessment, "context.ai_context_present")

    if ai_context or (readme >= 80 and (adrs > 0 or glossary)):
        return 100, "ai-context/ already present, or strong README plus ADRs/glossary"
    if readme >= 60:
        return 70, "solid README"
    if readme >= 30:
        return 40, "partial README"
    if readme > 0:
        return 15, "minimal README"
    return 0, "no usable README or context signal"


def score_blast_radius_containment(assessment: dict, rubric: dict) -> tuple[int, str] | None:
    ids = ["ops.staging_env_declared", "structure.cross_stack_edge_count", "vcs.hotspots"]
    if not _require(assessment, ids):
        return None
    staging = _value(assessment, "ops.staging_env_declared")
    cross_edges = _value(assessment, "structure.cross_stack_edge_count") or 0

    if not staging:
        return 10, "no staging environment declared"
    if cross_edges == 0:
        return 100, "staging declared, no cross-stack coupling"
    if cross_edges <= 5:
        return 70, "staging declared, low cross-stack coupling"
    return 40, "staging declared, higher cross-stack coupling"


def score_analyzability(assessment: dict, rubric: dict) -> tuple[int, str] | None:
    if not _available(assessment, "structure.parser_coverage_pct"):
        return None
    coverage = _value(assessment, "structure.parser_coverage_pct") or 0
    if coverage >= 90:
        return 100, "parser coverage >= 90%"
    if coverage >= 70:
        return 70, "parser coverage >= 70%"
    if coverage >= 50:
        return 40, "parser coverage >= 50%"
    if coverage >= 20:
        return 15, "parser coverage >= 20%"
    return 0, "parser coverage below 20%"


DIMENSION_FUNCTIONS = {
    "build_reproducibility": score_build_reproducibility,
    "test_safety_net": score_test_safety_net,
    "change_demand": score_change_demand,
    "structural_modularity": score_structural_modularity,
    "stack_coherence": score_stack_coherence,
    "debt_containability": score_debt_containability,
    "context_availability": score_context_availability,
    "blast_radius_containment": score_blast_radius_containment,
    "analyzability": score_analyzability,
}


def evaluate_dimensions(assessment: dict, rubric: dict) -> list[dict]:
    results = []
    for dim_id, dim_def in rubric["dimensions"].items():
        fn = DIMENSION_FUNCTIONS[dim_id]
        outcome = fn(assessment, rubric)
        if outcome is None:
            results.append({
                "id": dim_id, "weight": dim_def["weight"], "available": False,
                "sub_score": None, "reason": "one or more backing metrics unavailable",
                "backing_metrics": dim_def["backing_metrics"],
            })
        else:
            sub_score, reason = outcome
            results.append({
                "id": dim_id, "weight": dim_def["weight"], "available": True,
                "sub_score": sub_score, "reason": reason,
                "backing_metrics": dim_def["backing_metrics"],
            })
    return results


def compute_weighted_score(dimensions: list[dict]) -> tuple[float | None, float]:
    available = [d for d in dimensions if d["available"]]
    total_weight = sum(d["weight"] for d in available)
    if total_weight == 0:
        return None, 0.0
    weighted_sum = sum(d["weight"] * d["sub_score"] for d in available)
    return round(weighted_sum / total_weight, 2), total_weight


# ---------------------------------------------------------------------------
# Verdict + trust level. Precedence documented in rubric.yaml's
# `verdict_precedence` and references/rubric-design.md.
# ---------------------------------------------------------------------------

def determine_verdict(assessment: dict, rubric: dict, gates: list[dict], weighted_score: float | None) -> dict:
    demand = _human(assessment, "roadmap_demand_next_2q")
    sunset = _human(assessment, "sunset_or_replatform_planned")

    if demand in ("none", "low") or sunset is True:
        reason = (
            f"roadmap demand is '{demand}'" if demand in ("none", "low")
            else "sunset/replatform is planned"
        )
        return {
            "verdict": "DO_NOT_ONBOARD",
            "verdict_reason": f"DO_NOT_ONBOARD override: {reason} — regardless of score or gate results.",
            "do_not_onboard_override_applied": True,
        }

    gates_all_passed = all(g["passed"] for g in gates)
    if not gates_all_passed:
        failing = [g["id"] for g in gates if not g["passed"]]
        return {
            "verdict": "ONBOARD_AFTER_REMEDIATION",
            "verdict_reason": f"Hard gate(s) failing: {', '.join(failing)}. Verdict capped regardless of score.",
            "do_not_onboard_override_applied": False,
        }

    onboard_now_min = rubric["thresholds"]["onboard_now_min_score"]
    remediation_min = rubric["thresholds"]["onboard_after_remediation_min_score"]

    if weighted_score is None:
        return {
            "verdict": "ONBOARD_AFTER_REMEDIATION",
            "verdict_reason": "All gates passed, but no dimension had enough data to compute a score.",
            "do_not_onboard_override_applied": False,
        }
    if weighted_score >= onboard_now_min:
        return {
            "verdict": "ONBOARD_NOW",
            "verdict_reason": f"All gates passed and weighted score {weighted_score} >= {onboard_now_min}.",
            "do_not_onboard_override_applied": False,
        }
    if weighted_score >= remediation_min:
        return {
            "verdict": "ONBOARD_AFTER_REMEDIATION",
            "verdict_reason": f"All gates passed; weighted score {weighted_score} is in the "
                               f"[{remediation_min}, {onboard_now_min}) remediation band.",
            "do_not_onboard_override_applied": False,
        }
    if demand == "heavy":
        return {
            "verdict": "DEFER",
            "verdict_reason": f"Weighted score {weighted_score} < {remediation_min}, but roadmap demand "
                               f"is heavy — real investment required, revisit after remediation.",
            "do_not_onboard_override_applied": False,
        }
    return {
        "verdict": "ONBOARD_AFTER_REMEDIATION",
        "verdict_reason": f"Weighted score {weighted_score} < {remediation_min} and demand is not heavy; "
                           f"gates pass so the autonomy floor exists — still worth a remediation attempt.",
        "do_not_onboard_override_applied": False,
    }


def recommend_trust_level(gates: list[dict], verdict: str, rubric: dict) -> dict:
    """Phase 0 can only ever recommend a STARTING level of L0 or L1 — L2-L4 are
    explicitly earned through operating history (see trust_levels' gate_to_advance),
    which a first-time assessment cannot have observed yet."""
    trust_levels = rubric["trust_levels"]
    if verdict == "DO_NOT_ONBOARD":
        return {"recommended_starting_trust_level": None, "evidence_gate_to_advance": None}

    gates_all_passed = all(g["passed"] for g in gates)
    level = "L1" if gates_all_passed else "L0"
    gate_to_advance = trust_levels[level]["gate_to_advance"]
    return {"recommended_starting_trust_level": level, "evidence_gate_to_advance": gate_to_advance}


def score(assessment: dict, rubric: dict) -> dict:
    if assessment["rubric_version"] != rubric["rubric_version"]:
        raise RubricVersionMismatch(
            f"assessment-inputs.json targets rubric_version "
            f"{assessment['rubric_version']!r} but rubric.yaml is "
            f"{rubric['rubric_version']!r}"
        )

    gates = evaluate_gates(assessment, rubric)
    dimensions = evaluate_dimensions(assessment, rubric)
    weighted_score, total_available_weight = compute_weighted_score(dimensions)
    verdict_info = determine_verdict(assessment, rubric, gates, weighted_score)
    trust_info = recommend_trust_level(gates, verdict_info["verdict"], rubric)

    return {
        "schema_version": "1.0",
        "rubric_version": rubric["rubric_version"],
        "assessment_id": assessment["assessment_id"],
        "input_generated_at": assessment["generated_at"],
        "gates": gates,
        "gates_all_passed": all(g["passed"] for g in gates),
        "dimensions": dimensions,
        "weighted_score": weighted_score,
        "total_available_weight": total_available_weight,
        **verdict_info,
        **trust_info,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Score an assessment-inputs.json against rubric.yaml")
    parser.add_argument("assessment_path")
    parser.add_argument("--rubric", type=str, default=str(DEFAULT_RUBRIC_PATH))
    parser.add_argument("--out", type=str, default=None)
    args = parser.parse_args(argv)

    assessment = json.loads(Path(args.assessment_path).read_text())
    rubric = load_rubric(Path(args.rubric))
    result = score(assessment, rubric)

    output_json = json.dumps(result, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(output_json)
        print(f"✅ wrote {args.out}")
    else:
        print(output_json, end="")

    print(
        f"verdict={result['verdict']} score={result['weighted_score']} "
        f"trust_level={result['recommended_starting_trust_level']}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
